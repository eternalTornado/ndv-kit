---
module: <MODULE>
plan-source: <specsRoot>/<MODULE>/plan.md
approved: false               # /ndv-tasks set true qua AskUserQuestion gate — không tự set
approved-date:
created: <yyyy-mm-dd>
updated: <yyyy-mm-dd>
---

# Tasks — <MODULE>

> Ordered theo phase = dependency order của plan skeleton. Một task = một reviewable
> unit (≤1 file cluster), map về FR. `[P]` = parallelizable trong cùng phase.
> Test task theo TEST POLICY của host rules. KHÔNG estimate.
> Task đã `[x]` là immutable — plan delta sinh REWORK task mới, không uncheck.

## Phase 1 — <tầng thấp nhất của skeleton, vd Data/Model>

- [ ] T-001 [FR-001] <verb> <deliverable> (`<path/file>`)
- [ ] T-002 [P] [FR-002] …
- [ ] T-00V VERIFY: build/compile sạch theo cơ chế verify của project (`verifyNote` config), không error mới

## Phase 2 — <tầng kế, vd Logic>

- [ ] T-010 [FR-…] …
- [ ] T-01V VERIFY: build/compile sạch, không error mới

## Phase 3 — <wiring/registration>

- [ ] T-020 [FR-…] <entry/registration class + wiring theo module convention host>
- [ ] T-021 <registration artifact nếu host convention yêu cầu — sinh bằng cơ chế host quy định>
- [ ] T-02V VERIFY: module init/startup hoạt động theo acceptance criteria

## Phase 4 — <adapter/UI bind nếu có>

- [ ] T-030 [FR-…] …
- [ ] T-03V VERIFY: <acceptance criteria nào cover được bằng manual check>

## Coverage check

| FR | Tasks |
|---|---|
| <MODULE>-FR-001 | T-001 |

<Mọi FR phải xuất hiện ≥1 task; task không có FR ref phải justify từ plan.md.>
