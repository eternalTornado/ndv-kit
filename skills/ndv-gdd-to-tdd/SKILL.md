---
name: ndv-gdd-to-tdd
description: "Bước 1 pipeline ndvkit: chuyển GDD section thành Technical Design Document (<tddRoot>/<Feature>/tdd.md) — chỉ giữ technical concern. Idempotent: chạy lại trên GDD đã đổi = update TDD hiện có. Dùng khi có GDD mới, GDD update, hoặc cần TDD cho feature chưa có."
argument-hint: "<gdd-path-or-feature-name> [--update]"
user-invocable: true
allowed-tools: Read, Glob, Grep, Write, Edit, Task, AskUserQuestion, TodoWrite
---

When this skill is invoked:

## Phase 0 — Config & rules

Read `.claude/ndvkit/ndvkit.config.json` (`gddRoot`, `tddRoot`, `templates`). Rule source +
precedence do agent `tdd-writer` tự resolve (host `.claude/rules/**` > kit
`.claude/ndvkit/rules/**`).

## Parse arguments

- `<gdd-path-or-feature-name>` — a path under `<gddRoot>/**` OR a feature name
  to resolve by Glob against `<gddRoot>/**`. If ambiguous (multiple GDD files
  match), AskUserQuestion with the candidates.
- No argument → list GDD files that have no corresponding
  `<tddRoot>/<Feature>/tdd.md` and ask which to process.

## Phase 1 — Scope & mode

1. Resolve the GDD path(s) by Glob. Fail with a clear message if `<gddRoot>` is missing or
   the file does not exist — do not invent a GDD. Do NOT read the GDD body here:
   `tdd-writer` reads it; reading it twice buys nothing.
2. Derive `<Feature>` id: PascalCase domain name from the GDD file/folder name; if the host
   rules define a feature-id/glossary scheme, follow it.
3. Check `<tddRoot>/<Feature>/tdd.md`:
   - exists → **update mode**: the agent re-checks every literal quote + GDD cite of the TDD
     against the GDD and rewrites only sections whose source changed (A→B: delete A write B,
     no changelog).
   - absent → **create mode**.

## Phase 2 — Delegate to tdd-writer agent

Spawn the `tdd-writer` agent (Task tool) with:
- the GDD path(s) in scope,
- target `<tddRoot>/<Feature>/tdd.md`,
- template `<templates>/tdd-template.md`,
- mode (create/update).

## Phase 3 — Review gate

1. Verify without re-reading the whole TDD: Grep `^## ` in the TDD = the template's section
   list; Grep 3 literal values from TDD §3 in the cited GDD file (each must match). A miss →
   resume the same agent instance with the miss.
2. Present to the user: TDD path, the agent's section summary, and the full
   `NEEDS CLARIFICATION` list.
3. If clarifications exist, AskUserQuestion to resolve them now — answers are written into
   the TDD, replacing the markers, kèm cite `decision: <yyyy-mm-dd> — "<answer>"` (R3; GDD vẫn
   là nơi Design cập nhật sau) — or defer (markers stay; the TDD is not ready for
   `/ndv-tdd-to-spec` until zero markers remain in the sections being specced).

## Phase 4 — Downstream reminder

Report next steps (do not auto-run):
- `/ndv-module-matrix` if the TDD introduces or re-scopes modules.
- `/ndv-tdd-to-spec <Feature>` once clarifications are resolved.
