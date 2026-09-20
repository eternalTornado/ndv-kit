---
name: ndv-tdd-to-spec
description: "Bước 3 pipeline ndvkit: trích một TDD thành per-module <specsRoot>/<MODULE>/requirement.md theo EARS format, trace về TDD section + GDD anchor. Idempotent: TDD đổi = update requirement của module bị ảnh hưởng. Dùng khi TDD mới hoàn thành hoặc TDD update."
argument-hint: "<tdd-feature> [<module-id>...]"
user-invocable: true
allowed-tools: Read, Glob, Grep, Write, Edit, Bash, Task, AskUserQuestion, TodoWrite
---

When this skill is invoked:

## Phase 0 — Config & rules

Read `.claude/ndvkit/ndvkit.config.json` (`tddRoot`, `specsRoot`, `matrixRoot`,
`contractsDoc`, `templates`). Rule source + precedence do agent `spec-writer` tự resolve
(host `.claude/rules/**` > kit `.claude/ndvkit/rules/**`).

## Parse arguments

- `<tdd-feature>` (required) — resolves `<tddRoot>/<Feature>/tdd.md`. Missing
  file → fail with message pointing at `/ndv-gdd-to-tdd`.
- `[<module-id>...]` — restrict to specific modules; omit = every module the
  TDD maps to.

## Phase 1 — Preconditions

1. Grep the TDD for `NEEDS CLARIFICATION` (the agent reads the body, not this skill). If the
   sections in scope still contain markers, STOP and list them — requirements are not
   extracted from unresolved design. Offer AskUserQuestion to resolve now; answers are written
   back into `<tddRoot>/<Feature>/tdd.md` — replacing each inline marker (kèm cite
   `decision: <yyyy-mm-dd> — "<answer>"`, R3) and updating the TDD's open-clarifications
   section — before `spec-writer` is dispatched. The
   TDD is the upstream source of truth: an answer that lives only in
   requirement.md leaves the marker to re-fire on the next module of the same
   TDD.
2. Read TDD §8 (Module mapping) + `<matrixRoot>/modules.json`. If a system the TDD describes
   has no module entry, STOP and point at `/ndv-module-matrix` first —
   requirement.md needs a settled module boundary to attach to.

## Phase 2 — Delegate to spec-writer agent

Spawn `spec-writer` (Task tool): ≤3 modules in scope → ONE agent nhận cả danh sách module
(TDD đọc một lần); nhiều hơn → chia batch 3 module/agent, các batch chạy song song. Prompt:
- TDD path + module ids của batch (mapping section → module do agent làm theo modules.json),
- target `<specsRoot>/<MODULE>/requirement.md` per module,
- template `<templates>/requirement-template.md`.

EARS shape, contract surface, `contract:` FR sống sót qua forward pass: contract của agent
`spec-writer` — không restate trong prompt.

## Phase 3 — Review & report

1. Verify each produced requirement.md: every requirement matches an EARS
   pattern (WHEN/WHILE/IF-THEN/WHERE/shall), has an ID, has a cite (TDD
   section, or `contract:` Source). If the host rules declare an
   authority/trust boundary, flag any requirement violating it as invalid.
2. If the module already has spec artifacts from another flow of the host,
   note the overlap to the user; do not modify that flow's artifacts.
3. Report: per-module requirement counts, open `NEEDS CLARIFICATION`,
   contract surface additions proposed for the host's contract registry
   (`contractsDoc`), `orphan-contract-FR` list returned by the agent.
4. Refresh status cho mọi module touched (không spawn agent):
   `python3 .claude/ndvkit/skills/ndv-sync/scripts/ndv_check.py --refresh-status <MODULE...> --write`
   — `status` re-derive theo `/ndv-module-matrix` §Status lifecycle (fallback không Python: xem
   section đó).
5. Next step: `/ndv-specify <MODULE>` per module.
