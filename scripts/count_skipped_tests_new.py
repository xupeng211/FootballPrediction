import re
from pathlib import Path

skip_count = {}
print("分析跳过的测试...")

# 扫描所有pytest测试文件
for py_file in Path("tests/unit").rglob("test_*.py"):
    if not py_file.exists():
        continue
    content = py_file.read_text()
    # 统计跳过标记
    skips = re.findall(r"@pytest\.mark\.skipif\([^)]+\)", content)
    skips += re.findall(r"pytest\.skip\(", content)

    if skips:
        skip_count[str(py_file)] = len(skips)

# 排序
sorted_skips = sorted(skip_count.items(), key=lambda x: x[1], reverse=True)
print(f"\n找到 {len(sorted_skips)} 个有跳过标记的测试文件")

# 找出需要移动的文件（跳过>=3个）
files_to_move = []
for file, count in sorted_skips:
    if count >= 3:
        files_to_move.append(file)
        print(f"  {count:3d} 跳过: {file}")

print(f"\n需要移动 {len(files_to_move)} 个文件（跳过>=3个）")
