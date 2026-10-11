---
name: ndv-tasks
description: "Bước 3 pipeline ndvkit (SDD tasks): từ plan.md đã approve tạo/refresh <specsRoot>/<MODULE>/tasks.md — ordered task list theo phase, mỗi task ≤1 file-cluster, map về FR. Gate AskUserQuestion approve trước khi /ndv-implement. Dùng khi plan mới approve hoặc plan revise."
argument-hint: "<module-id>"
user-invocable: true
allowed-tools: Read, Glob, Grep, Write, Edit, Bash, AskUserQuestion, TodoWrite
---

When this skill is invoked:

## Phase 0 — Config & rules

Read `.claude/ndvkit/ndvkit.config.json` (`specsRoot`, `matrixRoot`, `templates`,
`verifyNote`). Rule source: host `.claude/rules/**` + `CLAUDE.md` nếu có; domain nào
host không define → dùng kit default rules tại `.claude/ndvkit/rules/**` (test policy
default của kit: không sinh test task trừ khi user yêu cầu). Host thắng khi mâu thuẫn —
including TEST POLICY (some projects defer tests, some require them).

## Phase 1 — Preconditions

1. Read `<specsRoot>/<MODULE>/plan.md`; require frontmatter `approved: true`
   — else STOP, point at `/ndv-plan`.
2. Read existing `tasks.md` if present. Update mode: completed tasks (`[x]`)
   are immutable history — plan deltas append/modify only unstarted tasks; if
   a delta invalidates a completed task, surface it as a rework task, do not
   silently uncheck.
3. Read `<specsRoot>/<MODULE>/specify.md` §Contract surface (final) and
   `<matrixRoot>/modules.json` (`paths` of every module; fallback `[path]`).

## Phase 2 — Decompose

Fill `<templates>/tasks-template.md`:
- **Prerequisites**: one row per specify.md Contract surface row — derived, never hand-authored
  here. Copy `Owner FR` as-is (`contract-gap` stays `contract-gap`); `Verify` = the owner's symbol
  `<path>::<Type>.<Member>` when it already exists in code (open the file, R3), else `owner tasks`;
  `Chặn task` = every task that needs the row.
- **File ownership**: every path in a task's `<files>` sits under this module's `paths`, or under
  no module's `paths` (vd scene, prefab, manifest, registration artifact). A path under another
  module's `paths` is a `cross-module-task`: move the need to a Prerequisites row — it is never a
  task of this module.
- Phases in dependency order mirroring the plan skeleton (data/model trước,
  wiring/UI sau).
- Task format: `- [ ] T-NNN [FR-refs] <verb> <deliverable> (<files>)`.
  One task = one reviewable unit (≤1 file cluster).
  `<files>` lists paths; when a task edits a specific existing member, point at it by
  symbol `<path>::<Type>.<Member>` — never bare `:<line>`. Anchors inherited from
  plan.md are kept only as symbols; a line-only anchor in plan.md is not copied into
  tasks.md. Parallelizable tasks in
  the same phase marked `[P]`.
- Test tasks: theo test policy của host rules — nếu host defer tests thì
  KHÔNG sinh test task trừ khi user yêu cầu.
- NO effort estimates, no timeline.
- Verification task closing each phase: build/compile sạch theo cơ chế verify
  của project (`verifyNote` config — vd editor compile, CLI build).

## Phase 3 — Approval gate

1. Present the phase/task table + FR coverage check (every FR appears in ≥1
   task; orphan tasks — no FR ref — need justification from plan.md) + the
   Prerequisites table with every `contract-gap` row and every
   `cross-module-task` called out. A `contract-gap` does not block approval
   (the owner decides) — it blocks `/ndv-implement` Phase 0 for the tasks it
   names.
2. AskUserQuestion: "Approve tasks cho <MODULE>?" — Approve / Revise / Reject.
3. On Approve: frontmatter `approved: true` + date, then refresh status (tasks.md còn task
   mở kéo module đã có code về `planned` — `/ndv-module-matrix` §Status lifecycle):
   `python3 .claude/ndvkit/skills/ndv-sync/scripts/ndv_check.py --refresh-status <MODULE> --write`.
4. Next: `/ndv-implement <MODULE>`.
