---
name: ndv-audit-module
description: "Bước 5 pipeline ndvkit: audit một module đã implement qua agent module-auditor — requirement coverage, spec drift, module contract, rules compliance theo .claude/rules của project host. Output report Finding/Evidence/Impact tại <auditReportRoot>/. READ-ONLY trên code. Dùng sau /ndv-implement hoặc định kỳ."
argument-hint: "<module-id> [--all]"
user-invocable: true
allowed-tools: Read, Glob, Grep, Bash, Write, Task, AskUserQuestion, TodoWrite
---

When this skill is invoked:

## Phase 0 — Config & rules

Read `.claude/ndvkit/ndvkit.config.json` (`specsRoot`, `matrixRoot`,
`auditReportRoot`). Compliance criteria: host `.claude/rules/**` + `CLAUDE.md` nếu có;
domain nào host không define → dùng kit default rules tại `.claude/ndvkit/rules/**`.
Host thắng khi mâu thuẫn.

## Parse arguments

- `<module-id>` — one module; `--all` — every modules.json entry with
  `status: "implemented"` (spawn auditors in parallel, one per module).

## Phase 1 — Preconditions

1. Resolve the module folder from `<matrixRoot>/modules.json` (`path` field);
   verify it exists.
2. Locate spec artifacts: `<specsRoot>/<MODULE>/specify.md` (fallback
   `requirement.md`; neither → audit runs rules/contract axes only and the
   report states coverage axis `N/A — no spec artifact`).

## Phase 2 — Delegate to module-auditor agent

Spawn `module-auditor` (Task tool) with module id, code path, spec paths,
modules.json entry, and report target
`<auditReportRoot>/<MODULE>-<yyyy-mm-dd>.md`. The agent is read-only on code;
findings follow Finding/Evidence/Impact + severity theo taxonomy đóng R7
(`blocker · critical · high · medium · low · info`); Evidence cite theo R1 audit
carve-out (`<path>::<Type>.<Member>:<line>`, hoặc `<path>:<line>` cho file không
có symbol) + literal quote; mỗi finding là `- [ ] **F-NNN**` trong `## Findings`
để `/ndv-audit-fix` parse; verdict `PASS | PASS-WITH-FINDINGS | FAIL`.

## Phase 3 — Triage

1. Relay the verdict + coverage table + findings (most severe first) to the
   user — the agent's report is not shown automatically.
2. Per finding cluster, AskUserQuestion routing:
   - **code fix** → hand the approved batch to `/ndv-audit-fix`, or the
     host's own fix flow if one exists,
   - **spec fix** (drift where the code is right) → `/ndv-sync` to update
     specify/plan (A→B replace),
   - **register fix** (`register-lag`: a built `plannedDeps` edge not yet in
     `deps`) → `/ndv-module-matrix <MODULE>`; no code or spec change,
   - **accept/defer** → record decision in the report's Triage section.
3. On FAIL verdict, run `/ndv-module-matrix <MODULE>`: `status` re-derives per
   §Status lifecycle (rời `implemented`) until a re-audit passes.
