---
name: ndv-tasks
description: "Bước 4c pipeline ndvkit (SDD tasks): từ plan.md đã approve tạo/refresh <specsRoot>/<MODULE>/tasks.md — ordered task list theo phase, mỗi task ≤1 file-cluster, map về FR. Gate AskUserQuestion approve trước khi /ndv-implement. Dùng khi plan mới approve hoặc plan revise."
argument-hint: "<module-id>"
user-invocable: true
allowed-tools: Read, Glob, Grep, Write, Edit, AskUserQuestion, TodoWrite
---

When this skill is invoked:

## Phase 0 — Config & rules

Read `.claude/ndvkit/ndvkit.config.json` (`specsRoot`, `templates`,
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

## Phase 2 — Decompose

Fill `<templates>/tasks-template.md`:
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
   task; orphan tasks — no FR ref — need justification from plan.md).
2. AskUserQuestion: "Approve tasks cho <MODULE>?" — Approve / Revise / Reject.
3. On Approve: frontmatter `approved: true` + date.
4. Next: `/ndv-implement <MODULE>`.
