#!/usr/bin/env python3
"""V41.670 密钥猎手 - 深度搜索 JS 文件中的加密凭据."""

import re
import base64
from pathlib import Path
from collections import Counter

# 目标 JS 文件
JS_DIR = Path("logs/js_assets")

# 搜索模式
PATTERNS = {
    # PBKDF2 相关
    "pbkdf2": r'pbkdf2[^a-zA-Z]{0,50}',
    "sha256": r'sha256[^a-zA-Z]{0,50}',
    "iterations": r'iterations?\s*[:=]\s*\d{3,5}',

    # AES 解密
    "aes_decrypt": r'aes\s*\.\s*decrypt|decrypt\s*\(\s*[^)]*\)',
    "aes_key": r'key\s*[:=]\s*["\']([^"\'}]{10,100})["\']',

    # Base64 字符串 (可能是密码或盐值)
    "long_base64": r'["\']([A-Za-z0-9+/]{40,150}={0,2})["\']',

    # 特殊字符组合 (可能是密码)
    "special_chars": r'["\']([^\w\s]{20,80})["\']',

    # 包含 OddsPortal 的长字符串
    "oddsportal_string": r'["\']([^"\']{20,150}OddsPortal[^"\']*)["\']',

    # IV 提取模式
    "iv_extract": r'iv\s*[:=]\s*[^,;\n]{10,100}',

    # CryptoJS 导入
    "cryptojs": r'CryptoJS|crypto-js',
}


def extract_minified_js_value(content: str, keyword: str) -> list:
    """从压缩代码中提取与关键词相关的值."""
    results = []

    # 查找关键词位置
    idx = 0
    while True:
        idx = content.lower().find(keyword.lower(), idx)
        if idx == -1:
            break

        # 获取前后 200 字符的上下文
        start = max(0, idx - 200)
        end = min(len(content), idx + 200)
        context = content[start:end]

        results.append((idx, context))
        idx += 1

    return results


def find_assignment_patterns(content: str) -> dict:
    """查找变量赋值模式，寻找可能的密码/盐值."""
    results = {
        "password_candidates": [],
        "salt_candidates": [],
        "key_candidates": [],
    }

    # 查找包含 password/pass/pwd/key/salt 的赋值
    assignment_patterns = [
        r'([a-zA-Z_$][a-zA-Z0-9_$]*)\s*=\s*["\']([^"\']{20,100})["\']',
        r'(["\']?[a-zA-Z_$][a-zA-Z0-9_$]*["\']?)\s*:\s*["\']([^"\']{20,100})["\']',
    ]

    for pattern in assignment_patterns:
        matches = re.finditer(pattern, content)
        for match in matches:
            var_name = match.group(1).strip('\'"')
            value = match.group(2)

            # 分类
            if any(kw in var_name.lower() for kw in ['pass', 'pwd']):
                results["password_candidates"].append((var_name, value))
            elif 'salt' in var_name.lower():
                results["salt_candidates"].append((var_name, value))
            elif 'key' in var_name.lower():
                results["key_candidates"].append((var_name, value))

    return results


def find_function_calls(content: str) -> list:
    """查找函数调用模式，特别是 PBKDF2/AES 相关."""
    results = []

    # PBKDF2 调用模式
    pbkdf2_patterns = [
        r'\.pbkdf2\s*\([^)]{100,500}\)',
        r'PBKDF2\s*\([^)]{100,500}\)',
        r'pbkdf2\s*\([^)]{100,500}\)',
    ]

    for pattern in pbkdf2_patterns:
        matches = re.finditer(pattern, content, re.IGNORECASE | re.DOTALL)
        for match in matches:
            results.append(("PBKDF2_CALL", match.group(0)))

    return results


def analyze_file(file_path: Path) -> dict:
    """分析单个 JS 文件."""
    print(f"\n{'='*60}")
    print(f"分析文件: {file_path.name}")
    print(f"{'='*60}")

    content = file_path.read_text(errors='ignore')

    results = {
        "file": file_path.name,
        "size": len(content),
        "findings": {},
    }

    # 1. 搜索所有模式
    for pattern_name, pattern in PATTERNS.items():
        matches = re.findall(pattern, content, re.IGNORECASE)
        if matches:
            results["findings"][pattern_name] = matches[:5]  # 限制输出

    # 2. 提取赋值模式
    assignments = find_assignment_patterns(content)
    if assignments["password_candidates"]:
        results["findings"]["password_assignments"] = assignments["password_candidates"][:5]
    if assignments["salt_candidates"]:
        results["findings"]["salt_assignments"] = assignments["salt_candidates"][:5]
    if assignments["key_candidates"]:
        results["findings"]["key_assignments"] = assignments["key_candidates"][:5]

    # 3. 搜索特定关键词上下文
    for keyword in ["password", "salt", "decrypt", "encrypt", "aes", "pbkdf2"]:
        contexts = extract_minified_js_value(content, keyword)
        if contexts:
            results["findings"][f"{keyword}_context"] = [(idx, ctx[:100]) for idx, ctx in contexts[:3]]

    return results


def main():
    """主函数."""
    print("V41.670 密钥猎手")
    print("=" * 60)

    # 重点文件
    priority_files = [
        "intercept.js",
        "app-OS_SrwcY.js",
        "lscompressor.min.js",
    ]

    all_results = []

    for filename in priority_files:
        file_path = JS_DIR / filename
        if not file_path.exists():
            print(f"文件不存在: {filename}")
            continue

        result = analyze_file(file_path)
        all_results.append(result)

        # 打印发现
        if result["findings"]:
            print(f"\n发现:")
            for key, value in result["findings"].items():
                print(f"  {key}: {value}")
        else:
            print("  未发现加密相关模式")

    # 汇总报告
    print(f"\n{'='*60}")
    print("汇总报告")
    print(f"{'='*60}")

    for result in all_results:
        if result["findings"]:
            print(f"\n文件: {result['file']}")
            for key, value in result["findings"].items():
                print(f"  {key}: {len(value) if isinstance(value, list) else 1} 项")

    # 保存完整结果
    output_file = Path("config/stealth/v41_670_crypto_findings.json")
    import json
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(json.dumps(all_results, indent=2, ensure_ascii=False), encoding='utf-8')
    print(f"\n完整结果已保存至: {output_file}")


if __name__ == "__main__":
    main()
