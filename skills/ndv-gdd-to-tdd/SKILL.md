---
name: ndv-gdd-to-tdd
description: "Bước 1 pipeline ndvkit: chuyển GDD section thành Technical Design Document (<tddRoot>/<Feature>/tdd.md) — chỉ giữ technical concern. Idempotent: chạy lại trên GDD đã đổi = update TDD hiện có. Dùng khi có GDD mới, GDD update, hoặc cần TDD cho feature chưa có."
argument-hint: "<gdd-path-or-feature-name> [--update]"
user-invocable: true
allowed-tools: Read, Glob, Grep, Write, Edit, Task, AskUserQuestion, TodoWrite
---

When this skill is invoked:

## Phase 0 — Config & rules

Read `.claude/ndvkit/ndvkit.config.json` (`gddRoot`, `tddRoot`, `templates`).
Rule source: host `.claude/rules/**` + `CLAUDE.md` nếu có; domain nào host không
define → dùng kit default rules tại `.claude/ndvkit/rules/**`. Host thắng khi mâu thuẫn.

## Parse arguments

- `<gdd-path-or-feature-name>` — a path under `<gddRoot>/**` OR a feature name
  to resolve by Glob against `<gddRoot>/**`. If ambiguous (multiple GDD files
  match), AskUserQuestion with the candidates.
- No argument → list GDD files that have no corresponding
  `<tddRoot>/<Feature>/tdd.md` and ask which to process.

## Phase 1 — Scope & mode

1. Read the resolved GDD file(s). Fail with a clear message if `<gddRoot>` is
   missing or the file does not exist — do not invent a GDD.
2. Derive `<Feature>` id: PascalCase domain name; if the host rules define a
   feature-id/glossary scheme, follow it.
3. Check `<tddRoot>/<Feature>/tdd.md`:
   - exists → **update mode**: diff-driven — only sections whose GDD source
     changed are rewritten (A→B: delete A write B, no changelog).
   - absent → **create mode**.

## Phase 2 — Delegate to tdd-writer agent

Spawn the `tdd-writer` agent (Task tool) with:
- the GDD path(s) in scope,
- target `<tddRoot>/<Feature>/tdd.md`,
- template `<templates>/tdd-template.md`,
- mode (create/update) and, in update mode, the changed GDD sections.

The agent extracts ONLY technical concerns (data, formulas literal-quoted,
state, flows, contracts, edge cases) and marks gaps `NEEDS CLARIFICATION`.

## Phase 3 — Review gate

1. Read the produced TDD; verify template sections are all present and every
   constant/formula carries a GDD cite (spot-check 3 values against source).
2. Present to the user: TDD path, section summary, and the full
   `NEEDS CLARIFICATION` list.
3. If clarifications exist, AskUserQuestion to resolve them now (answers are
   written into the TDD, replacing the markers) or defer (markers stay; the
   TDD is not ready for `/ndv-tdd-to-spec` until zero markers remain in the
   sections being specced).

## Phase 4 — Downstream reminder

Report next steps (do not auto-run):
- `/ndv-module-matrix` if the TDD introduces or re-scopes modules.
- `/ndv-tdd-to-spec <Feature>` once clarifications are resolved.
