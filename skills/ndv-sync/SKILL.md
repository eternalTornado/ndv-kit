---
name: ndv-sync
description: "Bước 6 pipeline ndvkit: delta orchestrator — khi GDD/TDD/ModuleMatrix/requirement/specify/plan/code đổi, detect artifact nào downstream bị stale và route đúng skill update (mọi skill trong kit đều idempotent). Dùng khi 'GDD vừa update', 'có module mới', 'spec đổi rồi', hoặc muốn health-check toàn pipeline."
argument-hint: "[gdd|tdd|matrix|spec|code <target>] [--check-only]"
user-invocable: true
allowed-tools: Read, Glob, Grep, Bash, Write, Edit, Task, AskUserQuestion, TodoWrite
---

When this skill is invoked:

## Phase 0 — Config & rules

Read `.claude/ndvkit/ndvkit.config.json` for all roots. Host
`.claude/rules/**` + `CLAUDE.md` là rule source ưu tiên; domain nào host không define
→ dùng kit default rules tại `.claude/ndvkit/rules/**`. Host thắng khi mâu thuẫn.

## Parse arguments

- `gdd|tdd|matrix|spec|code <target>` — the artifact tier that changed and
  its path/id. Omitted → full pipeline health-check (Phase 1 over
  everything).
- `--check-only` — report staleness, run nothing.

## Phase 1 — Staleness detection

The pipeline chain is `GDD → TDD → ModuleMatrix → requirement.md →
specify.md → plan.md → tasks.md → code`. An artifact is STALE when its
upstream source changed after it was last written. Detect with evidence:

1. `git log -1 --format=%cI -- <path>` per artifact (fallback: filesystem
   mtime for untracked files).
2. For a declared change (`gdd <path>` etc.), start at that tier and walk
   downstream only.
3. Content-level check where timestamps lie: TDD cites GDD anchors — Grep the
   anchors still exist; requirement cites TDD sections — same; modules.json
   `deps[]` vs actual import/using graph; plan.md `approved` flag predates a
   specify.md rewrite → approval is void.
   Artifact cites code: for every `<file>::<Symbol>` (and legacy `<file>.cs:<N>`) found in
   `<tddRoot>/**`, `<specsRoot>/**`, `<matrixRoot>/modules.json` — file exists under
   `codeRoots` AND the symbol grep-matches in it (legacy line anchor: the line still holds
   the quoted text or the symbol named beside it); a miss is `broken-cite`, a legacy
   line-only anchor that still lands is reported as `legacy-line-anchor` (informational,
   convert on next rewrite of the owning artifact).

## Phase 2 — Impact report

Present a table: artifact → status (`fresh | stale | broken-cite |
void-approval`) → evidence → skill to run. Example routes:

| Change | Route |
|---|---|
| GDD section edited | `/ndv-gdd-to-tdd <feature> --update` → then re-walk |
| TDD mới / TDD deps đổi | `/ndv-module-matrix <feature>` + `/ndv-tdd-to-spec <feature>` |
| Module mới xuất hiện trong code | `/ndv-module-matrix` (registration + layer) |
| requirement.md đổi | `/ndv-specify <MODULE>` |
| specify.md đổi sau khi plan approved | `/ndv-plan <MODULE>` (re-approve) |
| plan.md đổi sau khi tasks approved | `/ndv-tasks <MODULE>` (re-approve) |
| code đổi ngoài pipeline (hotfix) | `/ndv-audit-module <MODULE>` (drift check) |
| Code anchor `broken-cite` (symbol/line không còn khớp code) | re-anchor tại artifact sở hữu: TDD → `tdd-writer` refresh (Mode brownfield, chỉ sửa cite); requirement/specify → `/ndv-specify <MODULE>`; plan/tasks đã approved → sửa cite rồi `/ndv-plan` + `/ndv-tasks` re-approve; modules.json → `/ndv-module-matrix` |

`--check-only` stops here.

## Phase 3 — Guided execution

1. AskUserQuestion: which stale chains to update now (multiSelect).
2. Run the selected skills in upstream→downstream order, one tier at a time —
   each tier's output feeds the next tier's input, no skipping.
3. Approval gates are NOT bypassed: a re-run `/ndv-plan`/`/ndv-tasks` asks for
   approval again — sync never self-approves.
4. Report: chains updated, artifacts written, gates awaiting user.
