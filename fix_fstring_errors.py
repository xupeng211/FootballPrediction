#!/usr/bin/env python3
"""Fix f-string errors in processing_cache.py"""

# Read the file
with open(
    "src/services/processing/caching/processing_cache.py", "r", encoding="utf-8"
) as f:
    content = f.read()

# Fix patterns with extra quotes
content = content.replace('f"缓存命中: {cache_key}"', 'f"缓存命中: {cache_key}"')
content = content.replace(
    'f"使缓存失效: {invalidated_count} 个键"', 'f"使缓存失效: {invalidated_count} 个键"'
)
content = content.replace(
    'f"清理过期缓存完成，处理了 {len(keys)} 个键"',
    'f"清理过期缓存完成，处理了 {len(keys)} 个键"',
)

# Also fix the incorrect log messages
content = content.replace(
    'self.logger.warning(f"缓存命中: {cache_key}")',
    'self.logger.warning(f"缓存反序列化失败: {cache_key}")',
)
content = content.replace(
    'self.logger.error(f"缓存命中: {cache_key}")',
    'self.logger.error(f"获取缓存失败: {e}")',
)

# Write back
with open(
    "src/services/processing/caching/processing_cache.py", "w", encoding="utf-8"
) as f:
    f.write(content)

print("Fixed f-string errors")
