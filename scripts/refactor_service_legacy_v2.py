#!/usr/bin/env python3
"""
Refactor service_legacy.py - Split 975-line file into smaller modules
"""

import shutil
from pathlib import Path
from datetime import datetime


def analyze_file_structure():
    """Analyze file structure"""
    file_path = Path("src/services/audit_service_mod/service_legacy.py")

    with open(file_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    print(f"File total lines: {len(lines)}")
    print(f"File size: {file_path.stat().st_size / 1024:.2f} KB")

    # Analyze main components
    classes = []
    current_class = None
    methods = []

    for i, line in enumerate(lines, 1):
        if line.startswith("class "):
            if current_class:
                classes.append((current_class, methods))
            current_class = line.strip().split(":")[0]
            methods = []
        elif line.strip().startswith(("def ", "async def ")) and current_class:
            method_name = (
                line.strip().split("(")[0].replace("def ", "").replace("async ", "")
            )
            methods.append((method_name, i))

    if current_class:
        classes.append((current_class, methods))

    print("\nFile structure analysis:")
    for class_name, class_methods in classes:
        print(f"\n  {class_name}")
        for method_name, line_num in class_methods[:10]:  # Show first 10 methods
            print(f"    - {method_name} (line {line_num})")
        if len(class_methods) > 10:
            print(f"    ... and {len(class_methods) - 10} more methods")

    return classes


def create_refactor_plan():
    """Create refactor plan"""
    print("\n" + "=" * 80)
    print("📋 Refactor Plan")
    print("=" * 80)

    print(
        "\n🎯 Goal: Split service_legacy.py (975 lines) into multiple specialized modules"
    )

    print("\n📦 Suggested new module structure:")
    print("\n1. core.py - Core audit service class")
    print("   - AuditService main class")
    print("   - Basic initialization and configuration")

    print("\n2. data_sanitizer.py - Data sanitization and sensitive data handling")
    print("   - _hash_sensitive_value")
    print("   - _hash_sensitive_data")
    print("   - _sanitize_data")
    print("   - _is_sensitive_* related methods")

    print("\n3. audit_logger.py - Audit log recording")
    print("   - _create_audit_log_entry")
    print("   - log_operation")
    print("   - async_log_action")
    print("   - log_action")
    print("   - batch_log_actions")

    print("\n4. audit_query.py - Audit query and analysis")
    print("   - get_user_audit_summary")
    print("   - get_high_risk_operations")
    print("   - get_user_audit_logs")
    print("   - async_get_user_audit_logs")
    print("   - get_audit_summary")
    print("   - async_get_audit_summary")

    print("\n5. severity_analyzer.py - Severity and compliance analysis")
    print("   - _determine_severity")
    print("   - _determine_compliance_category")
    print("   - _contains_pii")


def backup_original_file():
    """Backup original file"""
    src = Path("src/services/audit_service_mod/service_legacy.py")
    dst = Path("src/services/audit_service_mod/service_legacy.py.bak")

    if not dst.exists():
        shutil.copy2(src, dst)
        print(f"\n✅ Backed up original file to: {dst}")
    else:
        print(f"\nℹ️ Backup file already exists: {dst}")


def create_module_files():
    """Create new module files"""
    base_path = Path("src/services/audit_service_mod")

    print("\n📝 Creating module files...")

    # Create __init__.py
    init_content = '''"""Audit Service Module

Provides complete audit functionality including data sanitization,
logging, querying and analysis.
"""

from .core import AuditService
from .data_sanitizer import DataSanitizer
from .audit_logger import AuditLogger
from .audit_query import AuditQueryService
from .severity_analyzer import SeverityAnalyzer

__all__ = [
    "AuditService",
    "DataSanitizer",
    "AuditLogger",
    "AuditQueryService",
    "SeverityAnalyzer",
]
'''

    init_file = base_path / "__init__.py"
    with open(init_file, "w", encoding="utf-8") as f:
        f.write(init_content)
    print(f"  ✅ Created: {init_file}")

    # Create placeholder modules
    modules = {
        "core.py": "Core Audit Service",
        "data_sanitizer.py": "Data Sanitization and Sensitive Data Handling",
        "audit_logger.py": "Audit Log Recording",
        "audit_query.py": "Audit Query and Analysis",
        "severity_analyzer.py": "Severity and Compliance Analysis",
    }

    for module_name, description in modules.items():
        module_file = base_path / module_name
        with open(module_file, "w", encoding="utf-8") as f:
            f.write(f'"""\n{description}\n\n[To be implemented]\n"""\n\n')
            f.write("from typing import Any, Dict, List, Optional\n")
            f.write("from src.core.logging import get_logger\n\n\n")
            f.write("class PlaceholderClass:\n")
            f.write('    """Placeholder class"""\n\n')
            f.write("    def __init__(self):\n")
            f.write("        self.logger = get_logger(__name__)\n\n")

        print(f"  ✅ Created: {module_file} (placeholder)")


def create_migration_guide():
    """Create migration guide"""
    guide = """# Service Legacy Refactor Migration Guide

## Overview
Split the 975-line `service_legacy.py` into 5 specialized modules:

1. **core.py** - Core audit service class (~100 lines)
2. **data_sanitizer.py** - Data sanitization and sensitive data handling (~200 lines)
3. **audit_logger.py** - Audit log recording (~250 lines)
4. **audit_query.py** - Audit query and analysis (~200 lines)
5. **severity_analyzer.py** - Severity and compliance analysis (~100 lines)

## Migration Steps

### Step 1: Create new modules
```bash
python scripts/refactor_service_legacy_v2.py
```

### Step 2: Migrate code gradually
1. Start with `data_sanitizer.py`
2. Then `severity_analyzer.py`
3. Then `audit_logger.py`
4. Then `audit_query.py`
5. Finally refactor `core.py`

### Step 3: Update imports
Update all files that import `service_legacy.py`:

```python
# Old import
from src.services.audit_service_mod.service_legacy import AuditService

# New import
from src.services.audit_service_mod import AuditService
```

### Step 4: Run tests
Ensure all tests pass:
```bash
make test-unit
```

### Step 5: Delete original file
After confirming everything works:
```bash
rm src/services/audit_service_mod/service_legacy.py
```

## Notes
- Keep original file as backup (`service_legacy.py.bak`)
- Migrate and test one module at a time
- Ensure no functionality is broken
- Update related documentation

## Completion Criteria
- [ ] All new modules created
- [ ] Code migrated from original file to new modules
- [ ] All tests pass
- [ ] Import statements updated
- [ ] Original file deleted
"""

    guide_path = Path("src/services/audit_service_mod/REFACTOR_GUIDE.md")
    with open(guide_path, "w", encoding="utf-8") as f:
        f.write(guide)

    print(f"\n✅ Created migration guide: {guide_path}")


def main():
    """Main function"""
    print("=" * 80)
    print("🔧 Service Legacy Refactor Tool")
    print(f"⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)

    # Analyze file structure
    analyze_file_structure()

    # Create refactor plan
    create_refactor_plan()

    # Backup original file
    backup_original_file()

    # Create module files (placeholders)
    create_module_files()

    # Create migration guide
    create_migration_guide()

    print("\n" + "=" * 80)
    print("✅ Refactor preparation complete!")
    print("=" * 80)

    print("\n📝 Next steps:")
    print("1. Review migration guide: src/services/audit_service_mod/REFACTOR_GUIDE.md")
    print("2. Migrate code to new modules one by one")
    print("3. Update import statements")
    print("4. Run tests to verify")
    print("5. Delete original file")


if __name__ == "__main__":
    main()
