---
name: ndv-module-matrix
description: "Bước 2 pipeline ndvkit: build/update ModuleMatrix — module dependency graph theo waterfall layer (L0 Foundation → Ln). Data ở <matrixRoot>/modules.json; view modules.md + field status do script ndv_check.py sinh (không tốn agent). Dùng khi có TDD mới, module mới, dependency đổi."
argument-hint: "[<tdd-feature> | <module-id>] [--verify]"
user-invocable: true
allowed-tools: Read, Glob, Grep, Write, Edit, Bash, Task, AskUserQuestion, TodoWrite
---

When this skill is invoked:

## Phase 0 — Config

Read `.claude/ndvkit/ndvkit.config.json` (`matrixRoot`, `tddRoot`, `specsRoot`, `codeRoots`,
`contractsDoc`, `auditReportRoot`). Module convention + rule precedence do agent
`module-architect` tự resolve (host `.claude/rules/**` > kit `.claude/ndvkit/rules/**`).

## Parse arguments

- `<tdd-feature>` — restrict the update to modules of one TDD; omit = full pass over all
  `<tddRoot>/**/tdd.md`.
- `<module-id>` — restrict the update to ONE modules.json entry: re-derive that module's
  `deps` from the code under its `paths`, promote every `plannedDeps` edge the code now
  references into `deps` with a grep-matched `depEvidence` cite, keep unreferenced planned
  edges planned, recompute layers. Other entries are preserved untouched. Used by
  `/ndv-implement` Phase 3 and register-fix của `/ndv-audit-fix`. An argument matching both a
  TDD feature and a module id → AskUserQuestion.
- `--verify` — read-only drift report, write nothing:
  `python3 .claude/ndvkit/skills/ndv-sync/scripts/ndv_check.py --checks deps` (+
  `--refresh-status` không `--write` = status drift). Stack script không hỗ trợ / không có
  Python → spawn `module-architect` với chỉ thị read-only.

Chỉ cần refresh `status` hoặc re-render `modules.md` → KHÔNG chạy skill này, gọi thẳng script
(§Status lifecycle).

## Phase 1 — Delegate to module-architect

Spawn `module-architect` (Task tool) với: scope (full / `<tdd-feature>` / `<module-id>`) +
path TDD trong scope. Agent tự đọc modules.json, TDD, contract docs, code — orchestrator
không đọc trước các file đó.

## Phase 2 — Validate, refresh, report

1. `python3 .claude/ndvkit/skills/ndv-sync/scripts/ndv_check.py --refresh-status <ids agent trả về> --write`
   (Windows: `python` / `py -3`) — derive `status` + sinh lại `<matrixRoot>/modules.md`.
   Script exit 2 = modules.json không parse / id lạ → feed lỗi về agent (resume).
2. Sanity-check: every `deps[]`/`plannedDeps[]` entry exists as a module id; `depEvidence`
   keys equal `deps`, `plannedDepEvidence` keys equal `plannedDeps`; each layer-N module only
   references layers < N over `deps ∪ plannedDeps`; `paths` không chồng nhau.
3. Report: layer table (layer → modules), new/changed modules, cycle or drift findings
   (Finding/Evidence/Impact), status changes script in ra, paths (`modules.json`, `modules.md`).

## Status lifecycle (SoT cho field `status` trong modules.json)

`status` là giá trị DERIVE từ artifact trên disk — không nhận từ prompt/TDD, agent không tự
suy. Đánh giá theo thứ tự, lấy dòng đầu khớp:

| status | Điều kiện |
|---|---|
| `implemented` | có source file dưới `paths` ∧ `<specsRoot>/<MODULE>/tasks.md` không còn task `- [ ]` (không có tasks.md = đạt — module brownfield) ∧ report module mới nhất `<auditReportRoot>/<MODULE>-*.md` không có verdict `FAIL` (chưa có report = đạt) |
| `planned` | `<specsRoot>/<MODULE>/plan.md` có frontmatter `approved: true` |
| `specced` | `<specsRoot>/<MODULE>/requirement.md` tồn tại |
| `proposed` | còn lại |

Hệ quả: module đã có code đang được mở rộng (tasks.md còn task mở) rơi về `planned`; mọi task
`[x]` mới trở lại `implemented`.

**Cách refresh** (mọi skill, không spawn agent, không invoke skill này):
`python3 .claude/ndvkit/skills/ndv-sync/scripts/ndv_check.py --refresh-status <MODULE> --write`.
Host không có Python → orchestrator tự đánh giá bảng trên bằng Glob/Grep rồi Edit đúng field
`status` của entry (modules.md khi đó không được sinh lại — ghi rõ trong report).

**Điểm refresh**: `/ndv-tdd-to-spec` (sau khi ghi requirement), `/ndv-plan` on Approve,
`/ndv-tasks` on Approve, `/ndv-implement` Phase 3, `/ndv-audit-code module` (mọi verdict),
`/ndv-onboard` matrix / reverse-doc.

## Update triggers (when to re-run this skill)

- New TDD or TDD dependency section changed → full pass.
- New module folder appears under `codeRoots` without a modules.json entry → full pass.
- `ndv_check.py --checks deps` báo `dep-undeclared` / `dep-declared-not-in-code` → `<module-id>`.
