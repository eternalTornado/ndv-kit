---
name: ndv-audit-standards
description: "Client standardization audit của UI estate against rules (host .claude/rules ưu tiên, fallback kit rules) — signature axis là STANDARDIZATION FOR RESKIN (client re-themeable như swap CSS theme). Lenses token-hygiene (mọi appearance literal né design token = per-line finding), naming/MVC/screen-key, element-name contract (bind graph C#↔markup), reuse/duplication, client-facing progress (screen/component/theme inventory). Protocol finder→verifier độc lập, ENUMERATE before GRADE, prior-report re-verify. Output findings dưới <auditReportRoot>/standards/. READ-ONLY trên project files. Song song với /ndv-audit-code (code quality/contract/parity)."
argument-hint: "[current [<path>] | changes vs-<base>]"
user-invocable: true
allowed-tools: Read, Grep, Glob, Bash, Write, Task, AskUserQuestion, TodoWrite
---

When this skill is invoked:

## User input

Accepted forms:

- `/ndv-audit-standards current` — audit toàn bộ client UI estate (full sweep, parallel
  FINDER agents).
- `/ndv-audit-standards current <path>` — full-sweep giới hạn subtree.
- `/ndv-audit-standards changes vs-<base>` — audit UI files changed vs `<base>`
  (`git diff <base>...HEAD --name-only`), COMMITTED-only: working tree bẩn → báo user
  commit rồi mới audit + STOP.
- Không có argument → AskUserQuestion hỏi mode. KHÔNG tự chọn.

Đây là client-standardization lens (reskin · UI naming · MVC · element-name · reuse). Code
quality / contract / parity / id KHÔNG thuộc skill này — đó là `/ndv-audit-code`.
Whole-estate review chạy CẢ HAI.

## Non-negotiables (áp dụng mọi step)

- **Signature axis = standardization for reskin.** Đổi theme = sửa MỘT token block, không
  sửa từng screen. MỌI style-sheet appearance literal ngoài token-definition block, MỌI
  markup inline-style literal (color/px), MỌI per-screen token-root fragment = per-line
  finding kèm fix cụ thể. Inline-style là surface phản-reskin sâu nhất, MANDATORY không defer.
- **Read-only trên project files.** File duy nhất được ghi là report dưới
  `<auditReportRoot>/standards/<run>/`. Fix là việc của `/ndv-audit-fix`.
- **Finder → Verifier, tách instance + convergence loop.** Candidate qua VERIFIER instance
  ĐỘC LẬP (agent `standards-auditor` vai VERIFIER); refuted vào `## Refuted` — KHÔNG drop
  im lặng. Loop tới khi finding-set đồng nhất, bound 3 round. Tally: raised = shipped +
  corrected + refuted.
- **ENUMERATE before GRADE.** Denominator per axis bằng formula re-runnable → `## Coverage`
  (screens = tập screen markup files; style_files; tokens = definitions trong token source;
  UI FR = spec UI requirements). `## Screen inventory` PHẢI phủ 100% screens — đây là MAP
  của reskin team.
- **Severity taxonomy đóng**: `blocker · critical · high · medium · low · info` (guide
  trong agent `standards-auditor`). Không mint mới.
- **WIP = note, không phải finding.** Pending re-wire (kit pitfalls P-08: dead bind kèm WIP
  signal) KHÔNG vào `## Findings` — đi vào `## Notes` (observational, không severity/Fix,
  không require fix). Chỉ genuine dead bind mới là finding.
- **Finding record đầy đủ**: Severity + Finding + Evidence (`path:line` + quote ≤2 dòng
  hoặc exact count + FULL hit list; dense repeats/1 file → 1 finding + count + example
  lines nhưng list per-file đủ) + Impact (rule + section) + Fix (before → after).
  `path:line` trong file này là viết tắt cho format R1 audit carve-out:
  `<path>::<Type>.<Member>:<line>` với file có symbol, `<path>:<line>` với file không có
  symbol (markup, stylesheet, data, asset); luôn kèm literal quote.
- **Exhaustive, không representative.** Sampling chỉ size `## Compliant`.
- **Metric có formula** (bảng chuẩn: rule ui-theming §Audit criteria) — không formula → OMIT.
- **Grep discipline.** Exclude third-party + engine-generated + build-artifact folders.
  Không BRE alternation `\|`.
- **Rule precedence**: host `.claude/rules/**`+`CLAUDE.md` > kit rules
  `.claude/ndvkit/rules/**`. Chỉ vào `## Rule conflicts — needs decision` khi priority
  không arbitrate.

## Step 0 — Load rules

Đọc `<auditReportRoot>/audit-learning.md` TRƯỚC TIÊN nếu có — áp dụng rule-for-next-run;
finding mới/recurring → append `L-NN`.

Resolve rule set (host trước, kit fallback):

| Lens | Rule files govern |
|---|---|
| token-hygiene | ui-theming (token single-source, literal ban, 8 axis, Audit criteria formulas) |
| naming/MVC/screen-key | naming-ui-toolkit + conventions (Controller/View, handler, suffix) |
| element-name contract | ui-theming §Element-name contract + known-pitfalls (pending re-wire) |
| reuse/duplication | ui-theming §Reuse + asset-structure §UI zones |
| progress | `<specsRoot>` UI specs + `<matrixRoot>/modules.json` + CLAUDE.md host (UI framework constraints, vd no runtime element construction) |

## Step 1 — Resolve scope

**`changes` mode:** dirty-check → diff → map file → lens (markup/style file → token-hygiene
+ naming; UI code file hoặc chứa bind helper → element-name contract; rule UI file đổi →
staleness cross-check).

**Anti-miss (MANDATORY) cho mỗi UI code file trong scope:** grep MỌI literal của MỌI helper
bind (`Q(`, `Q<`, `Query(`, `Bind(` + wrapper project-specific) — KHÔNG dừng ở cluster/helper
đầu tiên. Dựng author set = union element `name` của TOÀN BỘ markup estate (không chỉ file
changed), đối chiếu TỪNG literal. Literal ∉ author set = dead bind → finding, TRỪ WIP
(→ `## Notes`). Số literal check = số literal grep được — chênh = under-list, expand đủ.

≤50 files chạy inline (tự FINDER + spawn VERIFIER độc lập).

**`current` mode:** spawn 4 parallel FINDER agents (`subagent_type: standards-auditor`,
`run_in_background`): (1) token-hygiene + metric bảng, (2) naming/MVC/screen-key,
(3) element-name contract (anti-miss bắt buộc như trên), (4) reuse/duplication + progress +
inventories. Prompt: vai FINDER + lens + rule files + scope + ENUMERATE + exhaustive +
severity + output contract (CANDIDATES/METRICS/COVERAGE/INVENTORIES/FR_STATUS/COMPLIANT —
không tự đánh id). Agent type chưa đăng ký → `general-purpose` + nhồi đủ vào prompt.

## Step 2 — Collect + dedupe

Merge FINDER. Dedupe cùng `path(:line)` + rule; hai lens flag cùng file cho rule khác →
giữ cả hai. Đánh id tạm.

## Step 3 — Verify (verifier độc lập + convergence loop)

1. **Loop** (VERIFIER instance MỚI mỗi round, bound 3): spawn `standards-auditor` vai
   VERIFIER → verdict VERIFIED/CORRECTED/REFUTED + NEW (check carve-out: WIP pending
   re-wire, template alias, host carve-outs). Apply → hội tụ khi 0 CORRECTED + 0 NEW; chưa
   hội tụ sau 3 round → ship kèm flag `unstable`, ghi frontmatter `verification:`.
2. Orchestrator spot-check: Read cite line + confirm quote; count-based re-run grep.
3. Verify COMPLETENESS + `## Screen inventory` phủ 100% screens.

## Step 3b — Prior-report re-verify

Report MỚI NHẤT trong `<auditReportRoot>/standards/`: mỗi finding chưa fix re-verify →
resolved / still-present (carry, id mới + fresh `path:line`) / stale → `## Prior findings
re-verify`. Không có → "no baseline".

## Step 4 — Priority + conflict screen

Resolve overlap theo precedence; đã resolve sẵn trong rules (element name camelCase+suffix,
USS class kebab semantic, screen root `<screen>Root`, MVC Controller+View) → audit theo
winner, không report conflict. Conflict sống → C-xxx.

## Step 5 — Report

Ghi `<auditReportRoot>/standards/<YYYYMMDD-HHMM>-<mode>/<YYYYMMDD-HHMM>-<mode>.md`. `.md`
CANONICAL — không drop/rename section. Template sections (đúng tên): frontmatter (date,
job: client-standardization, mode, scope, git, verification tally) · `## Summary` ·
`## Coverage` · `## UI Health` (metric bảng ui-theming §Audit criteria gồm reskinReadyPct,
mỗi metric kèm formula) · `## Screen inventory` (100% screens) · `## Component inventory` ·
`## Theme variants` (palette clusters — mỗi cluster = hidden theme skin tương lai) ·
`## FR status` · `## Findings` (per lens, `- [ ] **F-NNN**`) · `## Rule conflicts — needs
decision` · `## Refuted` · `## Notes` (WIP items — fix-flow bỏ qua) · `## Prior findings
re-verify` · `## Compliant`.

Sau đó chat summary theo ngôn ngữ làm việc của project: tổng counts + verification tally +
severity breakdown + reskinReadyPct, anti-reskin blast-radius lớn nhất, link report.
Recommend `/ndv-audit-fix` — không tự bắt đầu fix.
