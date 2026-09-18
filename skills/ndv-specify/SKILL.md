---
name: ndv-specify
description: "Bước 4a pipeline ndvkit (SDD specify): từ <specsRoot>/<MODULE>/requirement.md tạo/refresh specify.md — EARS requirements đã clarified + acceptance criteria Given/When/Then. Resolve mọi ambiguity qua AskUserQuestion; specify.md hợp lệ khi zero NEEDS CLARIFICATION. Dùng khi requirement mới hoặc requirement đổi."
argument-hint: "<module-id>"
user-invocable: true
allowed-tools: Read, Glob, Grep, Write, Edit, Task, AskUserQuestion, TodoWrite
---

When this skill is invoked:

## Phase 0 — Config & rules

Read `.claude/ndvkit/ndvkit.config.json` (`specsRoot`, `templates`). Host
`.claude/rules/**` + `CLAUDE.md` là rule source ưu tiên; domain nào host không define
→ dùng kit default rules tại `.claude/ndvkit/rules/**`. Host thắng khi mâu thuẫn.

## Phase 1 — Load

1. Resolve `<module-id>`; read `<specsRoot>/<MODULE>/requirement.md` (missing
   → fail, point at `/ndv-tdd-to-spec`).
2. Read existing `specify.md` if present (update mode: only requirements whose
   requirement.md source changed are reworked; IDs are stable — never
   renumber).

## Phase 2 — Clarification loop

1. Collect every `NEEDS CLARIFICATION` marker and every requirement that is
   ambiguous by EARS standards (missing trigger, unmeasurable response,
   hidden multi-behavior, undefined term).
2. AskUserQuestion in batches (max 4 per call) with concrete options where the
   TDD/GDD constrains the answer (cite the source in the option description).
3. Write answers back into the requirements — the answer becomes the
   requirement text, not a footnote (A→B thay thế, không append).

## Phase 3 — Produce specify.md

Fill `<templates>/specify-template.md`:
- final EARS requirements (clarified),
- per-requirement acceptance criteria `Given/When/Then` — measurable; numeric
  representation theo convention của host rules (nếu có), không ambiguous
  quantifier ("vài", "nhiều", "khoảng"),
- scope boundary (in/out) + contract surface (what other modules must provide),
- traceability table: requirement ID → TDD section → GDD anchor.

## Phase 4 — Gate check

- Zero `NEEDS CLARIFICATION` remaining — else specify.md is not written;
  report what is still open instead.
- Every FR has ≥1 acceptance criterion.
- Report: requirement count, changed IDs, path. Next: `/ndv-plan <MODULE>`.
