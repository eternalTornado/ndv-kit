---
name: ndv-tdd-to-spec
description: "Bước 3 pipeline ndvkit: trích một TDD thành per-module <specsRoot>/<MODULE>/requirement.md theo EARS format, trace về TDD section + GDD anchor. Idempotent: TDD đổi = update requirement của module bị ảnh hưởng. Dùng khi TDD mới hoàn thành hoặc TDD update."
argument-hint: "<tdd-feature> [<module-id>...]"
user-invocable: true
allowed-tools: Read, Glob, Grep, Write, Edit, Task, AskUserQuestion, TodoWrite
---

When this skill is invoked:

## Phase 0 — Config & rules

Read `.claude/ndvkit/ndvkit.config.json` (`tddRoot`, `specsRoot`,
`matrixRoot`, `contractsDoc`, `templates`). Host `.claude/rules/**` +
`CLAUDE.md` là rule source ưu tiên; domain nào host không define → dùng kit default
rules tại `.claude/ndvkit/rules/**`. Host thắng khi mâu thuẫn.

## Parse arguments

- `<tdd-feature>` (required) — resolves `<tddRoot>/<Feature>/tdd.md`. Missing
  file → fail with message pointing at `/ndv-gdd-to-tdd`.
- `[<module-id>...]` — restrict to specific modules; omit = every module the
  TDD maps to.

## Phase 1 — Preconditions

1. Read the TDD. If the sections in scope still contain `NEEDS CLARIFICATION`,
   STOP and list them — requirements are not extracted from unresolved
   design. Offer AskUserQuestion to resolve now; answers are written back into
   `<tddRoot>/<Feature>/tdd.md` — replacing each inline marker and updating the
   TDD's open-clarifications section — before `spec-writer` is dispatched. The
   TDD is the upstream source of truth: an answer that lives only in
   requirement.md leaves the marker to re-fire on the next module of the same
   TDD.
2. Read `<matrixRoot>/modules.json`. If a system the TDD describes has no
   module entry, STOP and point at `/ndv-module-matrix` first —
   requirement.md needs a settled module boundary to attach to.

## Phase 2 — Delegate to spec-writer agent

Spawn `spec-writer` (Task tool) per module (parallel when multiple), each with:
- the TDD sections mapped to that module,
- target `<specsRoot>/<MODULE>/requirement.md`,
- template `<templates>/requirement-template.md`.

The agent writes EARS-only requirements (`<MODULE>-FR-NNN` /
`<MODULE>-NFR-NNN`), each citing its TDD source; cross-module needs go to the
Contract surface section, never absorbed as own scope.

## Phase 3 — Review & report

1. Verify each produced requirement.md: every requirement matches an EARS
   pattern (WHEN/WHILE/IF-THEN/WHERE/shall), has an ID, has a cite. If the
   host rules declare an authority/trust boundary, flag any requirement
   violating it as invalid.
2. If the module already has spec artifacts from another flow of the host,
   note the overlap to the user; do not modify that flow's artifacts.
3. Report: per-module requirement counts, open `NEEDS CLARIFICATION`,
   contract surface additions proposed for the host's contract registry
   (`contractsDoc`).
4. Run `/ndv-module-matrix <MODULE>` per module touched — `status` re-derives to `specced`
   (§Status lifecycle của skill đó).
5. Next step: `/ndv-specify <MODULE>` per module.
