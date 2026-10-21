---
name: ndv-module-matrix
description: "Maintenance ModuleMatrix của ndvkit: module dependency graph theo waterfall layer (L0 → Ln, topological — band Foundation nằm ở blueprint). Data ở <matrixRoot>/modules.json; view modules.md + field status do script ndv_check.py sinh (không tốn agent). Đăng ký module từ GDD nằm trong /ndv-blueprint-to-spec — skill này: full re-sync từ specs + code (không arg), re-derive một module từ code (<module-id>), --verify. Dùng khi module mới xuất hiện trong code, dependency đổi, hoặc sau implement."
argument-hint: "[<module-id>] [--verify]"
user-invocable: true
allowed-tools: Read, Glob, Grep, Write, Edit, Bash, Task, AskUserQuestion, TodoWrite
---

When this skill is invoked:

## Phase 0 — Config

Read `.claude/ndvkit/ndvkit.config.json` (`matrixRoot`, `specsRoot`, `codeRoots`,
`contractsDoc`, `auditReportRoot`). Module convention + rule precedence do agent
`module-architect` tự resolve (host `.claude/rules/**` > kit `.claude/ndvkit/rules/**`).

## Parse arguments

- Không argument → full re-sync: mọi entry modules.json re-derive từ `<specsRoot>/**` (Contract
  surface rows) + code dưới `codeRoots`.
- `<module-id>` — restrict the update to ONE modules.json entry: re-derive that module's
  `deps` from the code under its `paths`, promote every `plannedDeps` edge the code now
  references into `deps` with a grep-matched `depEvidence` cite, keep unreferenced planned
  edges planned, recompute layers. Other entries are preserved untouched. Used by
  `/ndv-implement` Phase 3 và register-fix của `/ndv-audit-fix`.
- `--verify` — read-only drift report, write nothing:
  `python3 .claude/ndvkit/skills/ndv-sync/scripts/ndv_check.py --checks deps` (+
  `--refresh-status` không `--write` = status drift). Stack script không hỗ trợ / không có
  Python → spawn `module-architect` (Task tool, model: sonnet) Mode full với chỉ thị read-only.

Chỉ cần refresh `status` hoặc re-render `modules.md` → KHÔNG chạy skill này, gọi thẳng script
(§Status lifecycle).

## Phase 1 — Delegate to module-architect

Spawn `module-architect` (Task tool): không arg → **Mode full** (model: opus); `<module-id>` →
**Mode module** (model: sonnet). Prompt chỉ mang mode + scope. Agent tự đọc modules.json,
specs, contract docs, code — orchestrator không đọc trước các file đó.

## Phase 2 — Validate, refresh, report

1. `python3 .claude/ndvkit/skills/ndv-sync/scripts/ndv_check.py --refresh-status <ids agent trả về> --write`
   (Windows: `python` / `py -3`) — derive `status` + sinh lại `<matrixRoot>/modules.md`.
   Script exit 2 = modules.json không parse / id lạ → feed lỗi về agent (resume).
2. Sanity-check: every `deps[]`/`plannedDeps[]` entry exists as a module id; `depEvidence`
   keys equal `deps`, `plannedDepEvidence` keys equal `plannedDeps`; each layer-N module only
   references layers < N over `deps ∪ plannedDeps`; `paths` không chồng nhau.
   `<matrixRoot>/blueprint.json` có → `python3 .claude/ndvkit/skills/ndv-blueprint/scripts/ndv_blueprint.py
   --check`: `matrix-band-violation` (module Foundation depend module `game`) = blocking finding;
   `edge-undeclared` / `unlisted-in-blueprint` → report, route `/ndv-blueprint --update`.
3. Report: layer table (layer → modules), new/changed modules, cycle or drift findings
   (Finding/Evidence/Impact), status changes script in ra, paths (`modules.json`, `modules.md`).

## Status lifecycle (SoT cho field `status` trong modules.json)

`status` là giá trị DERIVE từ artifact trên disk — không nhận từ prompt/spec, agent không tự
suy. Đánh giá theo thứ tự, lấy dòng đầu khớp:

| status | Điều kiện |
|---|---|
| `implemented` | có source file dưới `paths` ∧ `<specsRoot>/<NNN>_<MODULE>/tasks.md` không còn task `- [ ]` (không có tasks.md = đạt — module brownfield) ∧ report module mới nhất `<auditReportRoot>/<MODULE>-*.md` không có verdict `FAIL` (chưa có report = đạt) |
| `planned` | `<specsRoot>/<NNN>_<MODULE>/plan.md` có frontmatter `approved: true` |
| `specced` | `<specsRoot>/<NNN>_<MODULE>/requirement.md` tồn tại |
| `proposed` | còn lại |

Spec folder = field `spec` của entry, chưa có → Glob `<specsRoot>/*_<MODULE>/` (script:
`spec_folder_of`).

Hệ quả: module đã có code đang được mở rộng (tasks.md còn task mở) rơi về `planned`; mọi task
`[x]` mới trở lại `implemented`.

**Cách refresh** (mọi skill, không spawn agent, không invoke skill này):
`python3 .claude/ndvkit/skills/ndv-sync/scripts/ndv_check.py --refresh-status <MODULE> --write`.
Host không có Python → orchestrator tự đánh giá bảng trên bằng Glob/Grep rồi Edit đúng field
`status` của entry (modules.md khi đó không được sinh lại — ghi rõ trong report).

**Điểm refresh**: `/ndv-blueprint-to-spec` (sau stage author + sau stage specify), `/ndv-plan` on
Approve, `/ndv-tasks` on Approve, `/ndv-implement` Phase 3, `/ndv-audit-code module` (mọi
verdict), `/ndv-onboard` matrix / reverse-doc.

## Update triggers (when to re-run this skill)

- GDD mới / GDD đổi → KHÔNG phải skill này: `/ndv-blueprint-to-spec` (mapping + register nằm trong workflow).
- Contract surface row thêm/xóa ngoài `/ndv-blueprint-to-spec` (vd `/ndv-specify` Phase 4
  back-propagation / withdraw, requirement.md sửa tay) → full pass. Withdraw ở stage specify của
  `/ndv-blueprint-to-spec` không cần: skill đó tự register lại consumer.
- New module folder appears under `codeRoots` without a modules.json entry → full pass.
- `ndv_check.py --checks deps` báo `dep-undeclared` / `dep-declared-not-in-code` → `<module-id>`.
