---
name: ndv-audit-code
description: "Code-audit toàn estate against rules (host .claude/rules ưu tiên, fallback kit rules) + specs — grade PROGRESS (FR status vs code), CONTRACT (API/parity/content-parity, nửa tier này), QUALITY (metrics), DUPLICATION. Protocol finder→verifier độc lập (refuted không biến mất im lặng), ENUMERATE before GRADE, prior-report re-verify. Output findings (Severity/Evidence/Impact/Fix) dưới <auditReportRoot>/code/. READ-ONLY trên project files. Song song với /ndv-audit-standards (UI reskin/naming); khác /ndv-audit-module (một module vs spec của nó)."
argument-hint: "[current [<path>] | changes vs-<base>]"
user-invocable: true
allowed-tools: Read, Grep, Glob, Bash, Write, Task, AskUserQuestion, TodoWrite
---

When this skill is invoked:

## User input

Accepted forms:

- `/ndv-audit-code current` — audit toàn bộ code estate (full sweep, parallel FINDER agents).
- `/ndv-audit-code current <path>` — full-sweep giới hạn một subtree.
- `/ndv-audit-code changes vs-<base>` — audit files changed trên branch vs `<base>`
  (`git diff <base>...HEAD --name-only`), COMMITTED-only: `git status --porcelain` không
  rỗng → báo user commit hết rồi mới audit + STOP.
- Không có argument → AskUserQuestion hỏi mode. KHÔNG tự chọn.

Đây là code-audit lens (progress · contract · quality · parity · duplication). UI reskin /
UI naming / token-hygiene KHÔNG thuộc skill này — đó là `/ndv-audit-standards`. Whole-estate
review chạy CẢ HAI.

## Non-negotiables (áp dụng mọi step)

- **Read-only trên project files.** File duy nhất được ghi là report artifacts dưới
  `<auditReportRoot>/code/<run>/`. Không fix gì — fix là việc của `/ndv-audit-fix`
  (hoặc host fix-flow nếu có).
- **Finder → Verifier, tách instance + convergence loop.** Candidate từ FINDER phải qua
  VERIFIER instance ĐỘC LẬP (agent `code-auditor` vai VERIFIER) re-open tại `path:line` và
  cố refute trước khi vào report. Refuted vào `## Refuted` kèm refute_reason — KHÔNG BAO GIỜ
  drop im lặng. Verify chạy LOOP tới khi finding-set đồng nhất (round không còn
  correction/new), bound 3 round. Tally: raised = shipped + corrected + refuted.
- **Verify cái GIỮ, không chỉ cái ĐỔI.** Mỗi dòng `## Compliant` và mỗi count/claim audit
  giữ nguyên PHẢI mang formula re-runnable và được verifier re-run độc lập — "compliant"
  không bao giờ assert mà không có adversary.
- **Detection-method independence.** Verifier + regression re-check dùng phương pháp phát
  hiện KHÁC finder (enumerate-then-filter / semantic re-read) — pattern mù chạy lại y nguyên
  sẽ mù hai lần.
- **Property, không proxy.** Count/claim đo ĐÚNG property đang assert, không đo cái dễ-grep
  thay thế; cái khó grep (dead code, live-path binding) bắt buộc kiểm.
- **ENUMERATE before GRADE.** Denominator cố định per axis bằng formula re-runnable →
  `## Coverage` (modules từ module register/`<matrixRoot>/modules.json` ∪ specced-but-absent;
  endpoints = union route literals; source files trong scope; FR từ `<specsRoot>` specs).
  `covered + na == total`, hụt → caveat theo tên.
- **Severity taxonomy đóng**: `blocker · critical · high · medium · low · info`
  (guide trong agent `code-auditor`). Không mint mới.
- **Finding record đầy đủ**: Severity + Finding (1 câu) + Evidence (`path:line` + literal
  quote ≤2 dòng, hoặc exact count + FULL hit list) + Impact (rule/spec file + section) +
  Fix (before → after) — Fix bắt buộc cho severity ≥ low. `path:line` trong file này là
  viết tắt cho format R1 audit carve-out: `<path>::<Type>.<Member>:<line>` với file có
  symbol, `<path>:<line>` với file không có symbol (markup, stylesheet, data, asset); luôn
  kèm literal quote.
- **Exhaustive, không representative.** Finding pattern list MỌI occurrence project-wide.
  Parity-critical domain → sampling FORBIDDEN.
- **Metric có formula** — không formula → OMIT.
- **Tier scope.** Finding cross-tier chỉ verify được nửa repo này — ghi rõ "other tier
  unverifiable from this repo". Spec↔code conflict là FINDING, không nghiêng về spec.
- **Grep discipline.** Exclude third-party + engine-generated + build-artifact folders theo
  repo-hygiene host. Không BRE alternation `\|`.
- **Rule precedence**: host `.claude/rules/**`+`CLAUDE.md` > kit rules
  `.claude/ndvkit/rules/**`; trong kit `Shared/` > stack. Priority arbitrate được → audit
  theo rule thắng, cite nó. Chỉ vào `## Rule conflicts — needs decision` khi priority KHÔNG
  arbitrate.

## Step 0 — Load rules + specs

Đọc `<auditReportRoot>/audit-learning.md` TRƯỚC TIÊN nếu có (cross-run learning log) — áp
dụng mọi rule-for-next-run; surface finding mới/recurring → append `L-NN` (`pattern · root
cause · rule-for-next-run · evidence`).

Resolve rule set per lens (host trước, kit fallback):

| Lens | Rule/spec files govern |
|---|---|
| constitution/patterns | constitution + module-constraints (module shape, hot-path budget, hardcoded content) |
| naming | conventions (+ stack coding-style) |
| id | id-plan (kit invariants + host id table) |
| asset | asset-structure |
| contract/progress | `<specsRoot>/<MODULE>/` artifacts + `contractsDoc` + `<matrixRoot>/modules.json` + security (trust boundary) |
| cross-stack quality | Shared coding-style/security + CLAUDE.md host |

## Step 1 — Resolve scope

**`changes` mode:** dirty-check → diff `<base>...HEAD` → map file → lens (source code →
constitution+naming+id; HTTP adapter/route literal → thêm contract; content asset/data
table → asset+id; rule/spec file đổi → staleness cross-check với code reality). ≤50 files
chạy inline (tự FINDER + vẫn spawn VERIFIER độc lập).

**`current` mode:** spawn 5 parallel FINDER agents (`subagent_type: code-auditor`,
`run_in_background`), mỗi agent một lens: (1) constitution/patterns, (2) naming, (3) id,
(4) asset + content-parity, (5) contract/progress/duplication. Prompt mỗi agent: vai
`FINDER` + lens + rule files resolved ở Step 0 + scope + ENUMERATE trước + exhaustive +
property-not-proxy + severity + output contract (CANDIDATES/FR_STATUS/METRICS/COVERAGE/
COMPLIANT — không tự đánh id). Agent type chưa đăng ký trong session → dùng
`general-purpose` và nhồi đủ vai/lens/rules/output-contract vào prompt.

## Step 2 — Collect + dedupe

Merge FINDER (hoặc inline). Dedupe candidate cùng `path(:line)` + rule. Hai lens flag cùng
file cho rule KHÁC nhau → giữ cả hai. Đánh id tạm.

## Step 3 — Verify (verifier độc lập + convergence loop)

1. **Loop** (VERIFIER instance MỚI mỗi round, bound 3): spawn agent `code-auditor` vai
   VERIFIER với candidate set → verdict VERIFIED/CORRECTED/REFUTED + NEW candidates. Apply:
   CORRECTED update tại chỗ; REFUTED → `## Refuted`; NEW → thêm set. Round trả 0
   CORRECTED và 0 NEW → hội tụ, thoát. Chưa hội tụ sau 3 round → DỪNG, candidate tranh chấp
   ship kèm flag `unstable`, ghi vào frontmatter `verification:`.
2. Orchestrator spot-check: mỗi finding sẽ vào report, Read cite line + confirm quote;
   count-based re-run grep. Không reproduce → sửa hoặc REFUTED.
3. **Compliant/kept adversary pass**: verifier re-run độc lập formula của MỖI dòng
   compliant + MỖI kept claim, detection method khác finder. Không reproduce → thành
   candidate finding. Không formula → không được ship compliant.
4. Verify COMPLETENESS: pattern under-list site → expand đủ. Cross-doc claim → sweep MỌI
   doc trong tập cố định.

## Step 3b — Prior-report re-verify

Report MỚI NHẤT trong `<auditReportRoot>/code/` (nếu có): (1) open finding → re-verify →
resolved / still-present (carry, id mới + fresh `path:line`) / stale; (2) fixed finding →
re-run formula + whole-pattern re-sweep (fix một site nhưng sibling-site sót = finding
MỚI); (3) compliant/kept claim cũ → re-attack độc lập. Kết quả vào `## Prior findings
re-verify`. Không có baseline → ghi "no baseline".

## Step 4 — Priority + conflict screen

Resolve overlap theo precedence. Rule-doc staleness (doc nói A, code reality B) là finding
category riêng, cite cả hai phía. `## Rule conflicts — needs decision` (C-xxx) chỉ khi
priority không arbitrate.

## Step 5 — Report

Ghi `<auditReportRoot>/code/<YYYYMMDD-HHMM>-<mode>/<YYYYMMDD-HHMM>-<mode>.md`. `.md` là
CANONICAL — không drop/rename section. Template sections (đúng tên): frontmatter (date, job:
code-audit, mode, scope, git, verification tally) · `## Summary` · `## Coverage` ·
`## Metrics` ·
`## FR status` · `## Findings` (per lens; mỗi finding `- [ ] **F-NNN**` + Severity/Evidence/
Impact/Fix) · `## Rule conflicts — needs decision` (C-NNN) · `## Refuted` (R-NNN) ·
`## Prior findings re-verify` · `## Compliant` (mỗi dòng kèm formula re-runnable).

Sau đó chat summary theo ngôn ngữ làm việc của project: tổng counts + verification tally +
severity breakdown, finding blast-radius lớn nhất, link report. Recommend `/ndv-audit-fix`
— không tự bắt đầu fix.
