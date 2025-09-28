# Coverage Diagnosis Summary

## Quick Results

- **Total files with <10% coverage**: 25 files
- **Files with 0% coverage**: 20 files
- **Files with existing but failing tests**: 2 files
- **Files completely missing tests**: 23 files

## Key Findings

### Test File Issues (92% of problems)
- 23 files have no corresponding test files
- Main affected modules: API, Monitoring, Streaming, Tasks
- Total untested code: ~4,000 lines

### Test Execution Issues (8% of problems)
- `src/monitoring/alert_manager.py`: Prometheus registry conflict
- `src/tasks/streaming_tasks.py`: Import function mismatch

## Priority Actions

1. **Fix existing failing tests** (2 files) - Quick wins
2. **Create tests for high-impact modules** (5-8 files) - Medium effort
3. **Build comprehensive test coverage** (remaining files) - Long term

## Expected Coverage Impact

- **Current**: 16%
- **After fixing existing tests**: 18-19%
- **After core module tests**: 26-31%
- **Complete coverage**: 40-50%

See `docs/_reports/COVERAGE_DIAGNOSIS.md` for detailed analysis.