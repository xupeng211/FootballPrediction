#!/usr/bin/env python3
"""
针对性修复语法错误
"""

import re
from pathlib import Path

def fix_specific_errors():
    """修复特定的语法错误"""
    print("开始针对性修复语法错误...\n")
    
    # 修复 main.py
    print("修复 src/main.py...")
    fix_main_py()
    
    # 修复 app.py
    print("\n修复 src/api/app.py...")
    fix_app_py()
    
    # 修复其他文件
    print("\n修复其他关键文件...")
    fix_other_files()
    
    print("\n✓ 修复完成！")

def fix_main_py():
    """修复 main.py 的语法错误"""
    file_path = Path('src/main.py')
    if not file_path.exists():
        print("  - 文件不存在，跳过")
        return
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 修复 limiter 配置
    content = re.sub(
        r'limiter = Limiter\(\s*\n\s*key_func=get_remote_address,\s*\n\s*default_limits=\[\)\s*\n\s*"100/minute",\s*\n\s*"1000/hour",\s*\n\s*,\s*\n\s*storage_uri=.*?\s*\n\s*headers_enabled=True,\s*\n\s*\)',
        r'''limiter = Limiter(
        key_func=get_remote_address,
        default_limits=[
            "100/minute",
            "1000/hour",
        ],
        storage_uri=os.getenv("REDIS_URL", "memory://"),
        headers_enabled=True,
    )''',
        content,
        flags=re.DOTALL
    )
    
    # 修复 return 语句
    content = re.sub(
        r'return \{\)\s*\n\s*"service":.*?\s*\n\s*"version":.*?\s*\n\s*"status":.*?\s*\n\s*"docs_url":.*?\s*\n\s*"health_check":.*?\s*\n\s*\}',
        r'''return {
        "service": "足球预测API",
        "version": "1.0.0",
        "status": "运行中",
        "docs_url": "/docs",
        "health_check": "/api/health",
    }''',
        content,
        flags=re.DOTALL
    )
    
    # 修复 JSONResponse 语句
    content = re.sub(
        r'return JSONResponse\(\)\s*\n\s*status_code=exc\.status_code,\s*\n\s*content=\{\)\s*\n\s*"error": True,\s*\n\s*"status_code":.*?\s*\n\s*"message":.*?\s*\n\s*"path":.*?\s*\n\s*,\s*\n\s*\)',
        r'''return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": True,
            "status_code": exc.status_code,
            "message": exc.detail,
            "path": str(request.url),
        },
    )''',
        content,
        flags=re.DOTALL
    )
    
    # 修复另一个 JSONResponse
    content = re.sub(
        r'return JSONResponse\(\)\s*\n\s*status_code=500,\s*\n\s*content=\{\)\s*\n\s*"error": True,\s*\n\s*"status_code": 500,\s*\n\s*"message":.*?\s*\n\s*"path":.*?\s*\n\s*,\s*\n\s*\)',
        r'''return JSONResponse(
        status_code=500,
        content={
            "error": True,
            "status_code": 500,
            "message": "内部服务器错误",
            "path": str(request.url),
        },
    )''',
        content,
        flags=re.DOTALL
    )
    
    # 修复 uvicorn.run
    content = re.sub(
        r'uvicorn\.run\(\)\s*\n\s*"src\.main:app",\s*\n\s*host=host,\s*\n\s*port=port,\s*\n\s*reload=.*?\s*\n\s*log_level="info",\s*\n\s*\)',
        r'''uvicorn.run(
        "src.main:app",
        host=host,
        port=port,
        reload=os.getenv("ENVIRONMENT") == "development",
        log_level="info",
    )''',
        content,
        flags=re.DOTALL
    )
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print("  ✓ main.py 修复完成")

def fix_app_py():
    """修复 app.py 的语法错误"""
    file_path = Path('src/api/app.py')
    if not file_path.exists():
        print("  - 文件不存在，跳过")
        return
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 修复 root 函数定义
    content = re.sub(
        r'@app\.get\("/"\)\s*\n\s*async def root\(\)\s*\n:',
        r'@app.get("/")\nasync def root():\n',
        content
    )
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print("  ✓ app.py 修复完成")

def fix_other_files():
    """修复其他文件的语法错误"""
    files_to_fix = [
        'src/api/predictions.py',
        'src/api/predictions/__init__.py',
        'src/api/data/__init__.py',
        'src/utils/string_utils.py',
        'src/utils/__init__.py',
        'src/utils/crypto_utils.py',
        'src/utils/data_validator.py',
        'src/utils/time_utils.py'
    ]
    
    for file_path in files_to_fix:
        path = Path(file_path)
        if not path.exists():
            continue
        
        try:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 修复常见的括号错误
            content = content.replace('[)', '[]')
            content = content.replace('{)', '{}')
            content = content.replace('(,)', '(None,)')
            content = content.replace('__all__ = [)', '__all__ = []')
            
            # 修复字典和列表
            content = content.replace('dict {)', 'dict {}')
            content = content.replace('list {)', 'list []')
            content = content.replace('tuple {)', 'tuple ()')
            content = content.replace('set {)', 'set {}')
            
            # 修复 return 语句
            content = content.replace('return [)', 'return []')
            content = content.replace('return {)', 'return {}')
            
            # 写回文件
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            print(f"  ✓ {file_path} 修复完成")
            
        except Exception as e:
            print(f"  ✗ {file_path} 修复失败: {e}")

if __name__ == '__main__':
    fix_specific_errors()
