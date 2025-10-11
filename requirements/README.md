# Requirements 文件说明

## 文件结构

- `base.txt` - 生产环境核心依赖
- `dev.txt` - 开发环境依赖（包含 base.txt）
- `test.txt` - 测试依赖（包含 base.txt）
- `optional.txt` - 可选功能依赖（ML、Streaming等）
- `requirements.lock` - 完整的依赖锁定文件
- `README.md` - 本说明文档

## 使用方式

### 生产环境
```bash
pip install -r base.txt
```

### 开发环境
```bash
pip install -r dev.txt
```

### 测试环境
```bash
pip install -r test.txt
```

### 安装可选依赖
```bash
pip install -r optional.txt
```

### 完整环境（包含所有依赖）
```bash
pip install -r requirements.lock
```

## 依赖管理

使用 pip-tools 管理依赖：

```bash
# 更新锁定文件
pip-compile requirements.in

# 同步环境
pip-sync requirements.txt
```

## 历史变更

- 2025-10-12: 从18个文件简化为6个核心文件
