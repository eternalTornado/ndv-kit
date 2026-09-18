---
name: ndv-module-matrix
description: "Bước 2 pipeline ndvkit: build/update ModuleMatrix — module dependency graph theo waterfall layer (L0 Foundation → Ln), data ở modules.json, render index.html (HTML+CSS light theme, self-contained). Dùng khi có TDD mới, module mới, dependency đổi, hoặc cần re-render."
argument-hint: "[<tdd-feature> | <module-id>] [--render-only | --verify]"
user-invocable: true
allowed-tools: Read, Glob, Grep, Write, Edit, Bash, Task, AskUserQuestion, TodoWrite
---

When this skill is invoked:

## Phase 0 — Config & rules

Read `.claude/ndvkit/ndvkit.config.json` (`matrixRoot`, `tddRoot`,
`specsRoot`, `codeRoots`, `contractsDoc`, `templates`). Rule source: host
`.claude/rules/**` + `CLAUDE.md` nếu có; domain nào host không define → dùng kit
default rules tại `.claude/ndvkit/rules/**`. Host thắng khi mâu thuẫn.

## Parse arguments

- `<tdd-feature>` — restrict the update to modules of one TDD; omit = full
  pass over all `<tddRoot>/**/tdd.md`.
- `<module-id>` — restrict the update to ONE modules.json entry (an id from the
  host's module table). Used by `/ndv-implement` Phase 3 and `/ndv-audit-module`
  register-fix: re-derive that module's `deps` from the code under its `path`,
  promote every `plannedDeps` edge the code now references into `deps` with a
  grep-matched `depEvidence` cite, keep unreferenced planned edges planned,
  recompute layers, re-render. Re-derive `status` per §Status lifecycle. Other
  entries are preserved untouched. An argument matching both a TDD feature and
  a module id → AskUserQuestion.
- `--render-only` — regenerate `<matrixRoot>/index.html` from the existing
  `<matrixRoot>/modules.json` without recomputing the graph.
- `--verify` — read-only: recompute layers from specs + code import/using
  graph and report drift against modules.json; write nothing.

## Phase 1 — Inputs

1. Read `<matrixRoot>/modules.json` if present (update mode — preserve
   entries not in scope).
2. Read the TDD(s) in scope, the host's module convention rules, and the
   cross-module contract/dependency docs (`contractsDoc`, `<specsRoot>/**`)
   for declared dependencies.

## Phase 2 — Delegate to module-architect agent

Spawn `module-architect` (Task tool) with scope + the layering rules reminder:
- Layer 0 = foundation (no project-module deps); layer(M) = 1 + max(layer(deps)).
- Cycle = blocking finding (propose interface split, do not auto-resolve).
- Verify declared deps against actual import/using graph under `codeRoots`;
  drift is a finding.

Agent writes `<matrixRoot>/modules.json` and regenerates
`<matrixRoot>/index.html` from `<templates>/module-matrix-template.html`
(inject modules.json into `<script id="module-data" type="application/json">`;
the template is self-contained inline-CSS light theme — no external assets,
no CDN).

## Phase 3 — Validate & report

1. Sanity-check the JSON parses; every `deps[]` and `plannedDeps[]` entry exists as a
   module id; `depEvidence` keys equal `deps`, `plannedDepEvidence` keys equal
   `plannedDeps`. `rootRel` khớp độ sâu của `matrixRoot` (`docs/ModuleMatrix` → `../../`).
   `status` mỗi entry khớp §Status lifecycle.
2. Check each layer-N module only references layers < N, over `deps ∪ plannedDeps`.
3. Report to the user: layer table (layer → modules), new/changed modules,
   cycle or drift findings (Finding/Evidence/Impact), and the file paths.
   Suggest opening `<matrixRoot>/index.html` in a browser.

## Status lifecycle (SoT cho field `status` trong modules.json)

`status` là giá trị DERIVE, không nhận từ prompt/TDD. Chỉ skill này (qua `module-architect`)
ghi field này; skill khác cần refresh thì invoke `/ndv-module-matrix <MODULE>`. Đánh giá theo
thứ tự, lấy dòng đầu khớp:

| status | Điều kiện |
|---|---|
| `implemented` | có source file dưới `path` ∧ report `<auditReportRoot>/<MODULE>-*.md` mới nhất (frontmatter `job: module-audit`) không có verdict `FAIL` (chưa có report = đạt) |
| `planned` | `<specsRoot>/<MODULE>/plan.md` có frontmatter `approved: true` |
| `specced` | `<specsRoot>/<MODULE>/requirement.md` tồn tại |
| `proposed` | còn lại |

Điểm refresh trong pipeline: `/ndv-tdd-to-spec` (→ `specced`), `/ndv-plan` on Approve
(→ `planned`), `/ndv-implement` Phase 3 (→ `implemented`), `/ndv-audit-module` on `FAIL`
(rời `implemented`), `/ndv-onboard` Option 2/3.

## Update triggers (when to re-run this skill)

- New TDD or TDD dependency section changed → full pass.
- New module folder appears under `codeRoots` without a modules.json entry →
  full pass (status derive theo §Status lifecycle).
- Style/rendering tweak → `--render-only`.
