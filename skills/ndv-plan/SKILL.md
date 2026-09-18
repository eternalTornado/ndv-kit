---
name: ndv-plan
description: "Bước 4b pipeline ndvkit (SDD plan): từ specify.md tạo/refresh <specsRoot>/<MODULE>/plan.md — technical design (module skeleton, types, data flow, wiring) theo module convention của project host. Kết thúc bằng gate AskUserQuestion approve; plan chưa approve thì không được implement. Dùng khi specify mới/đổi hoặc design cần revise."
argument-hint: "<module-id>"
user-invocable: true
allowed-tools: Read, Glob, Grep, Write, Edit, AskUserQuestion, TodoWrite
---

When this skill is invoked:

## Phase 0 — Config & rules

Read `.claude/ndvkit/ndvkit.config.json` (`specsRoot`, `matrixRoot`,
`templates`). Rule source: host `.claude/rules/**` + `CLAUDE.md` nếu có; domain nào
host không define → dùng kit default rules tại `.claude/ndvkit/rules/**`. Host thắng
khi mâu thuẫn.

## Phase 1 — Load context

1. Read `<specsRoot>/<MODULE>/specify.md` (missing or containing
   `NEEDS CLARIFICATION` → fail, point at `/ndv-specify`).
2. Read the `<matrixRoot>/modules.json` entry (layer + allowed deps) and the
   contract surface docs of every dependency.
3. Read the host rules that bind the design: architecture/module conventions,
   naming, coding style, known pitfalls — whatever `.claude/rules/**` of the
   host declares.
4. Read existing `plan.md` if present — update mode preserves approved
   decisions unless the specify delta invalidates them (call those out).
5. Read the existing code the plan will extend: Glob the module `path` from the
   modules.json entry and Read every source file the design touches. Every as-built
   reference in plan.md cites `<path>::<Type>.<Member>` of a symbol opened in this
   session (R3) — anchors are never carried over from specify.md, the TDD, or
   modules.json without re-opening the file, and code is never cited by bare `:<line>`.

## Phase 2 — Design

Fill `<templates>/plan-template.md`:
- **Module skeleton**: folder layout, entry/registration class, namespace —
  ALL per the host module conventions. If the design needs a structure the
  host rules don't allow/declare, flag it as a decision for the user, not a
  silent deviation.
- **Types**: classes/interfaces per folder, suffix/naming per host rules.
- **Data flow**: how each FR is realized — component interaction, events,
  wire contracts (event/serialization conventions per host rules). Existing
  components/methods are named by symbol `<path>::<Type>.<Member>`; new ones by
  name + folder per the skeleton.
- **Dependency wiring**: the module's declared dependencies must equal the
  modules.json entry's `deps[] ∪ plannedDeps[]`; anything extra = go back to
  `/ndv-module-matrix` first (an edge the plan needs but code does not have yet
  belongs in `plannedDeps`, with spec evidence).
- **UI (if any)**: per the host UI conventions (framework, authoring rules,
  binding pattern).
- **Risks & pitfalls**: which host pitfalls apply and how the design avoids
  them.
- **FR → design element mapping table** (every FR lands somewhere).

Design decisions the spec does not constrain: pick ONE and justify with a
cite; if genuinely irreversible or user-taste, AskUserQuestion with 2-3
options.

## Phase 3 — Approval gate

1. Present the plan summary (skeleton + FR mapping + risks).
2. AskUserQuestion: "Approve plan cho <MODULE>?" — options: Approve / Revise
   (specify what) / Reject.
3. On Approve: set frontmatter `approved: true` + date in plan.md, then run
   `/ndv-module-matrix <MODULE>` (`status` → `planned`).
   On Revise: apply, re-ask. Never mark approved yourself without the answer.
4. Next: `/ndv-tasks <MODULE>`.
