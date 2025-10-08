import sys
from pathlib import Path

errors = []
for f in Path("tests").rglob("test_*.py"):
    text = f.read_text(encoding="utf-8")
    for i, line in enumerate(text.splitlines(), start=1):
        if "TODO" in line:
            errors.append(f"{f}:{i}: Found TODO placeholder → {line.strip()}")

if errors:
    print("❌ Found TODO placeholders in test files:")
    for e in errors:
        print("   ", e)
    print("\n请替换 TODO 为真实断言后再提交！")
    sys.exit(1)
else:
    print("✅ No TODO placeholders found in tests.")
