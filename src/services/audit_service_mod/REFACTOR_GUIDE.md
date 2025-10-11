# Service Legacy Refactor Migration Guide

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
