## PR Type

选择一个主类型：

- [ ] runtime-code-change
- [ ] governance-only
- [ ] docs-only
- [ ] test-only
- [ ] ci-fix
- [ ] data-artifact

## Runtime Behavior

- Runtime code change included: yes / no
- Runtime code paths changed: n/a
- Runtime behavior changed: n/a

如果这是 implementation phase 但没有 runtime code change，默认 No-Go。请说明原因、blocker 和人工确认：

- Explanation:
- Human confirmation:

## Artifact Scope

- Docs/report/manifest changes included: yes / no
- Added/modified report lines:
- Added/modified manifest lines:
- Copies full historical state: yes / no
- Includes large artifact: yes / no
- Large artifact justification, if any:

## Business Progress

- Business progress:
- Blocker removed:
- Blocker remaining:
- Next step:

## Safety Status

- no live fetch: yes / no / n/a
- no detail fetch: yes / no / n/a
- no network request: yes / no / n/a
- no DB writes: yes / no / n/a
- no raw_match_data inserts: yes / no / n/a
- no matches writes: yes / no / n/a
- no matches.external_id changes: yes / no / n/a
- no raw write execution: yes / no / n/a
- no re-acceptance execution: yes / no / n/a
- no suspension reversal: yes / no / n/a
- no rollback execution: yes / no / n/a
- no parser/features/training/prediction: yes / no / n/a
- no full body/raw_data/pageProps saved or printed: yes / no / n/a

If any answer is `no`, list the explicit authorization, scope, command, and verification:

- Authorization details:

## Tests Run

- [ ] lint
- [ ] unit tests
- [ ] coverage
- [ ] formatter
- [ ] git diff --check
- [ ] hidden/bidi scan
- [ ] full payload marker scan
- [ ] DB SELECT-only safety check, if applicable
- [ ] other:

Commands and results:

```text

```

## Review Notes

- Reviewer focus:
- Residual risk:
- Follow-up PR, if any:
