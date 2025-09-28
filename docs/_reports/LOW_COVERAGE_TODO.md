# Low Coverage Files TODO - Phase 4.3

## Current Status (2025-09-28)

### Overall Coverage
- **Current Coverage**: 17.84%
- **Target Coverage**: 25%+
- **Gap**: 7.16pp
- **Total Statements**: 12,013
- **Covered Statements**: 2,626

### Zero Coverage Files Summary
- **Total Zero-Coverage Files**: 15
- **Phase 4.3 Target**: Top 10 files by line count
- **Remaining After Phase 4.3**: 5 files

## Phase 4.3 Target Files (Top 10 by Line Count)

| Rank | File | Lines | Priority | Status |
|------|------|-------|----------|--------|
| 1 | `src/api/data.py` | 181 | High | 🟡 Target |
| 2 | `src/api/monitoring.py` | 177 | High | 🟡 Target |
| 3 | `src/lineage/metadata_manager.py` | 155 | High | 🟡 Target |
| 4 | `src/tasks/maintenance_tasks.py` | 150 | High | 🟡 Target |
| 5 | `src/data/collectors/streaming_collector.py` | 145 | High | 🟡 Target |
| 6 | `src/tasks/streaming_tasks.py` | 134 | Medium | 🟡 Target |
| 7 | `src/data/features/examples.py` | 126 | Medium | 🟡 Target |
| 8 | `src/api/predictions.py` | 123 | Medium | 🟡 Target |
| 9 | `src/lineage/lineage_reporter.py` | 110 | Medium | 🟡 Target |
| 10 | `src/api/features_improved.py` | 105 | Medium | 🟡 Target |

**Total Lines in Phase 4.3 Target**: 1,608 lines

## Remaining Files (After Phase 4.3)

| Rank | File | Lines | Priority | Status |
|------|------|-------|----------|--------|
| 11 | `src/tasks/utils.py` | 82 | Low | ⏳ Pending |
| 12 | `src/main.py` | 69 | Low | ⏳ Pending |
| 13 | `src/api/buggy_api.py` | 16 | Low | ⏳ Pending |
| 14 | `src/cache/consistency_manager.py` | 11 | Low | ⏳ Pending |
| 15 | `src/core/logging.py` | 5 | Low | ⏳ Pending |

**Total Lines in Remaining Files**: 183 lines

## Expected Impact

### Phase 4.3 Potential Impact
- **Target Files**: 1,608 lines across 10 files
- **Conservative Estimate**: 15-25% coverage per file = 241-402 lines covered
- **Optimistic Estimate**: 30-50% coverage per file = 482-804 lines covered
- **Coverage Impact**: +2.0pp to +6.7pp overall

### Post-Phase 4.3 Projection
- **Conservative**: 17.84% + 2.0pp = 19.84%
- **Optimistic**: 17.84% + 6.7pp = 24.54%
- **Gap to 25%**: 0.46pp to 5.16pp remaining

## Next Phase Planning

### Phase 4.4 (Remaining 5 Files)
- **Target**: Remaining 5 zero-coverage files (183 lines)
- **Strategy**: Aggressive testing to maximize coverage
- **Expected Impact**: +0.5pp to +2.0pp

### Phase 5 (Low Coverage Enhancement)
- **Target**: Files with <20% coverage
- **Strategy**: Enhanced testing and integration tests
- **Expected Impact**: +3pp to +8pp

## Success Criteria

### Phase 4.3 Success Metrics
- ✅ All 10 target files have measurable coverage (>0%)
- ✅ No zero-coverage files remain in top 10 targets
- ✅ Overall coverage increases by at least 2pp
- ✅ All new tests run without errors

### Final Target (25%+)
- **Minimum Requirement**: 25% overall coverage
- **Stretch Goal**: 27%+ overall coverage
- **Timeline**: Complete Phase 4.3 and 4.4

## Notes

- **File Availability**: Some files may not exist or may have import issues
- **Complexity**: Larger files may require more sophisticated testing strategies
- **Dependencies**: External dependencies may need complex mocking setups
- **Integration**: Consider integration tests for better coverage in complex modules

---
*Last Updated: 2025-09-28*
*Phase: 4.3 - Zero Coverage File Remediation*