---
name: ndv-audit-code
description: "Bước 5 pipeline ndvkit — skill audit DUY NHẤT của kit: grade code against bộ chuẩn trong rules (host .claude/rules ưu tiên, fallback kit rules) + spec. 3 scope: `module <id>` (một module vs spec của nó + rules, verdict PASS/FAIL nuôi status trong modules.json), `current [<path>]` (estate sweep), `changes vs-<base>` (diff branch). Protocol finder→verifier độc lập qua agent code-auditor. Output MỘT file report .md dưới <auditReportRoot>. READ-ONLY trên project files. Dùng sau /ndv-implement, trước merge, hoặc định kỳ."
argument-hint: "[module <module-id>... | module --all | current [<path>] | changes vs-<base>]"
user-invocable: true
allowed-tools: Read, Grep, Glob, Bash, Write, Task, AskUserQuestion, TodoWrite
---

When this skill is invoked:

## User input

- `module <module-id>...` — audit từng module vs spec của nó + rules; `module --all` = mọi
  entry modules.json có `status: "implemented"`.
- `current [<path>]` — sweep toàn code estate (hoặc một subtree).
- `changes vs-<base>` — files changed vs `<base>` (`git diff <base>...HEAD --name-only`),
  COMMITTED-only: `git status --porcelain` không rỗng → báo user commit rồi mới audit + STOP.
- Không argument → AskUserQuestion hỏi scope. KHÔNG tự chọn.

## Non-negotiables (phần của orchestrator)

- **Read-only trên project files.** File duy nhất được ghi là report `.md` (Step 5). Không fix
  gì — fix + triage là việc của `/ndv-audit-fix`.
- **Protocol sống trong agent `code-auditor`** (evidence format, ENUMERATE before GRADE,
  exhaustive, property-not-proxy, severity guide, carve-out, tier scope). Prompt spawn chỉ
  mang: vai · lens · rule/spec files · scope (· candidate set) — không restate protocol.
- **Finder → Verifier tách instance.** Mọi finding vào report đã qua VERIFIER độc lập;
  REFUTED vào `## Refuted` kèm refute_reason — không drop im lặng. Tally: raised = shipped +
  corrected + refuted.
- **Orchestrator không đóng vai FINDER và không tự re-verify finding** — chỉ merge, dedupe,
  đánh id, apply verdict, ghi report. Đọc lại evidence là việc của VERIFIER.
- **Severity**: tập đóng R7 (`Shared/ai-discipline.md` §R7). Không mint mới.
- **Rule precedence**: host `.claude/rules/**` + `CLAUDE.md` > kit rules
  `.claude/ndvkit/rules/**`; trong kit `Shared/` > stack. Priority arbitrate được → audit theo
  rule thắng, cite nó; chỉ vào `## Rule conflicts — needs decision` khi priority KHÔNG arbitrate.

## Step 0 — Config + resolve lens

Read `.claude/ndvkit/ndvkit.config.json` (`specsRoot`, `matrixRoot`, `auditReportRoot`,
`codeRoots`, `contractsDoc`, `rulesRoot`, `kitRulesRoot`). Resolve rule file per lens (host
trước, kit fallback) — chỉ truyền PATH cho agent, orchestrator không đọc body rule:

| Lens | Rule/spec files | Active khi scope có |
|---|---|---|
| `patterns` | constitution (Shared + stack) · module-constraints · Shared coding-style/security · known-pitfalls | source code |
| `naming` | conventions + stack coding-style | source code / asset |
| `data` | id-plan (+ host id table) · asset-structure | content asset, data table, id literal |
| `spec` | `<specsRoot>/<MODULE>/` (specify.md, fallback requirement.md) · `contractsDoc` · `<matrixRoot>/modules.json` · security (trust boundary) | module có spec artifact / route literal |
| `ui` | ui-theming · naming-ui-toolkit · known-pitfalls | markup / stylesheet / UI code chứa bind helper |

Lens không có file nào trong scope → không spawn cho lens đó; ghi `N/A` vào `## Coverage`.

## Step 1 — Scope + spawn FINDER

| Mode | Scope | FINDER |
|---|---|---|
| `module` | `paths` của module trong modules.json (fallback `[path]`; folder không tồn tại → fail). Không có specify.md lẫn requirement.md → lens `spec` = `N/A — no spec artifact`, chỉ chạy lens rules | MỘT FINDER per module, nhận mọi lens active; nhiều module → song song |
| `changes` | dirty-check → diff → map file → lens (rule/spec file đổi → thêm staleness cross-check với code reality) | ≤50 files: MỘT FINDER mọi lens; >50: một FINDER per lens active |
| `current` | estate (hoặc `<path>`) | một FINDER per lens active (≤5), song song, `run_in_background` |

`subagent_type: code-auditor`. Agent type chưa đăng ký trong session → `general-purpose` +
dòng đầu prompt: "Read `.claude/ndvkit/agents/code-auditor.md` và làm đúng vai <vai> trong đó".

## Step 2 — Collect + dedupe

Merge output FINDER. Dedupe candidate cùng evidence site + cùng rule; hai lens flag cùng file
cho rule KHÁC nhau → giữ cả hai. Đánh id tạm.

## Step 3 — Verify

VERIFIER input = candidate set + mọi dòng `COMPLIANT` (kèm formula) + prior findings của
baseline. Baseline = report mới nhất cùng loại (`module`: `<auditReportRoot>/<MODULE>-*.md`;
`current`/`changes`: mới nhất dưới `<auditReportRoot>/code/`); lấy finding còn `- [ ]` và
finding đã `- [x]`. Không có → ghi "no baseline".

- `module`: MỘT round VERIFIER per module.
- `current` / `changes`: loop, bound 3 round, instance MỚI mỗi round. Round N>1 chỉ nhận
  CORRECTED + NEW của round N-1 (không gửi lại set đã VERIFIED). Round trả 0 CORRECTED + 0
  NEW → hội tụ. Chưa hội tụ sau 3 round → candidate tranh chấp ship kèm flag `unstable`, ghi
  vào frontmatter `verification:`.

Apply verdict: CORRECTED update tại chỗ; REFUTED → `## Refuted`; NEW → thêm vào set;
`COMPLIANT` không reproduce → thành candidate; prior findings → `## Prior findings re-verify`
(still-present carry sang `## Findings` với id mới + evidence mới).

## Step 4 — Priority + conflict screen

Resolve overlap theo precedence. Rule-doc staleness (doc nói A, code reality B) là finding
category riêng, cite cả hai phía. Conflict priority không arbitrate → `C-NNN`.

## Step 5 — Report (một file `.md`)

- `module` → `<auditReportRoot>/<MODULE>-<yyyy-mm-dd>.md`
- `current` / `changes` → `<auditReportRoot>/code/<YYYYMMDD-HHMM>-<mode>.md`

Sections (đúng tên — `/ndv-audit-fix` parse theo tên): frontmatter (`date`, `job: code-audit`,
`mode`, `scope`, `module` + `verdict` khi mode `module`, `git`, `verification` tally) ·
`## Summary` · `## Coverage` · `## FR status` (mode `module`: bảng coverage mọi FR/NFR, bắt
buộc) · `## Metrics` (chỉ metric có formula) · `## Findings` (mỗi finding `- [ ] **F-NNN**` +
Severity/Finding/Evidence/Impact/Fix, severity giảm dần) · `## Rule conflicts — needs decision`
· `## Refuted` (R-NNN) · `## Notes` (WIP — fix-flow bỏ qua) · `## Prior findings re-verify` ·
`## Compliant` (mỗi dòng kèm formula).

Verdict (mode `module`): `FAIL` = còn finding `blocker`/`critical`, hoặc FR `missing` không
có deferral note trong spec; `PASS-WITH-FINDINGS` = có finding khác; `PASS` = không finding.

## Step 6 — Close

1. Mode `module`: refresh status mọi verdict —
   `python3 .claude/ndvkit/skills/ndv-sync/scripts/ndv_check.py --refresh-status <MODULE> --write`
   (không có Python → `/ndv-module-matrix` §Status lifecycle, sửa field `status` bằng tay).
2. Chat summary theo ngôn ngữ làm việc của project: verdict (mode `module`) + counts theo
   severity + verification tally + finding blast-radius lớn nhất + link report.
3. Next: `/ndv-audit-fix <report>` — skill đó own triage (code-fix / spec-fix / register-fix /
   defer). Không tự bắt đầu fix.
