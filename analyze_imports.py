import re
import subprocess

def find_missing_imports():
    result = subprocess.run(['ruff', 'check', 'src/', '--output-format=concise'],
                          capture_output=True, text=True)

    imports_needed = set()
    for line in result.stdout.split('\n'):
        if 'F821' in line:
            if 'np.' in line:
                imports_needed.add('numpy as np')
            elif 'pd.' in line:
                imports_needed.add('pandas as pd')

    return imports_needed

print(f'需要添加的导入: {find_missing_imports()}')
