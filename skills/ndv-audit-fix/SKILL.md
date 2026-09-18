---
name: ndv-audit-fix
description: "Fix-flow đóng vòng audit của kit: parse findings unchecked từ audit report (/ndv-audit-code, /ndv-audit-standards, /ndv-audit-module), triage per cluster (code-fix / spec-fix → /ndv-sync / defer), execute qua agent audit-fixer đúng Fix before→after (không mở rộng scope, không sweep sibling-site — prior-report re-verify của vòng audit sau own việc đó), verify compile theo verifyNote + orchestrator re-run Evidence formula, tick checkbox + ghi Triage vào report. Never commit. Dùng sau khi có audit report."
argument-hint: "[<report-path> | latest [code|standards|module]] [--ids F-001,F-002] [--severity <min>]"
user-invocable: true
allowed-tools: Read, Grep, Glob, Bash, Write, Edit, Task, AskUserQuestion, TodoWrite
---

When this skill is invoked:

## User input

Accepted forms:

- `/ndv-audit-fix <report-path>` — fix theo một report cụ thể (file `.md` canonical).
- `/ndv-audit-fix latest <code|standards|module>` — report mới nhất của loại đó dưới
  `<auditReportRoot>` (code: `code/<run>/`; standards: `standards/<run>/`; module: file dưới
  `<auditReportRoot>/` có frontmatter `job: module-audit`, mới nhất theo `date`; không match
  theo tên file, bỏ qua `onboard-*.md`).
- `--ids F-001,F-002` — chỉ fix các finding id liệt kê (validate id tồn tại + unchecked
  sau khi parse).
- `--severity <min>` — lọc theo taxonomy đóng `blocker · critical · high · medium · low ·
  info` (vd `--severity high` = blocker + critical + high).
- Không argument → AskUserQuestion chọn report. KHÔNG tự chọn.

## Non-negotiables (áp dụng mọi step)

- **Chỉ fix finding có trong report.** Không drive-by refactor, không sweep sibling-site
  ngoài hit list của finding — sibling sót là finding MỚI của vòng audit sau
  (prior-report re-verify của audit skill own việc đó).
- **Skip set cố định**: `## Refuted`, `## Notes` (WIP), finding đã tick `- [x]`. Finding
  flag `unstable` hoặc thiếu `Fix (before → after)` → KHÔNG auto-fix, gom vào nhóm
  needs-decision hỏi user.
- **`## Rule conflicts — needs decision` (C-NNN) không bao giờ auto-fix** — luôn
  AskUserQuestion; user chưa quyết → giữ nguyên.
- **Verify hai tầng per batch**: compile theo `verifyNote` của config + orchestrator ĐỘC LẬP
  re-run Evidence formula per finding — formula còn hit tại site đã fix = finding chưa chết,
  KHÔNG tick.
- **Report update tối thiểu**: tick `- [x]` + append/update `## Triage` — không xóa/rename/
  reorder section nào khác (`.md` là CANONICAL của audit skill).
- **Never commit.** Kết thúc recommend user commit rồi chạy re-audit `changes vs-<base>`.
- **Rule precedence**: host `.claude/rules/**` + `CLAUDE.md` > kit rules
  `.claude/ndvkit/rules/**` — như mọi skill trong kit.

## Step 0 — Config + resolve report

Read `.claude/ndvkit/ndvkit.config.json` (`auditReportRoot`, `verifyNote`, `specsRoot`,
`matrixRoot`). Resolve report theo user input; đọc frontmatter `job:` để biết loại:

| job (frontmatter) | Findings ở đâu | Đặc thù parse |
|---|---|---|
| `code-audit` | `## Findings` per lens, `- [ ] **F-NNN**` | skip `## Refuted`; flag `unstable` → needs-decision |
| `client-standardization` | như trên | thêm skip `## Notes` (WIP) |
| `module-audit` | `## Findings`, `- [ ] **F-NNN**` (như estate report; không có `## Refuted`/`## Notes`) | verdict `FAIL` → sau fix recommend re-run `/ndv-audit-module <module>` để `status` re-derive trong modules.json |

## Step 1 — Parse findings

Extract mọi finding unchecked, giữ nguyên record (id · severity · Finding · Evidence
`path:line` + quote · Impact · Fix before→after). Apply filter `--ids` / `--severity`.
Đối chiếu tổng: số finding parse được phải khớp số `- [ ]` trong section — chênh =
parse sót, sửa parse trước khi tiếp tục. `path:line`
trong file này là viết tắt cho format R1 audit carve-out: `<path>::<Type>.<Member>:<line>`
với file có symbol, `<path>:<line>` với file không có symbol (markup, stylesheet, data,
asset); luôn kèm literal quote.

## Step 2 — Triage gate

Cluster findings theo file-cluster (các finding chạm cùng file/folder) + lens.
AskUserQuestion per cluster (>4 cluster → gộp câu hỏi theo nhóm severity):

- **code-fix** — mặc định cho finding có Fix rõ, code sai rules/spec.
- **spec-fix** — code đúng, spec/rule/doc sai (drift) → KHÔNG sửa code; ghi Triage, route
  `/ndv-sync` update artifact.
- **defer** — ghi Triage kèm lý do của user, không tick.

`--ids` được coi là user đã pre-triage code-fix cho các id đó — vẫn hỏi lại khi finding
thuộc category rule-doc staleness / spec↔code conflict (bản chất là spec-fix candidate).

## Step 3 — Execute (agent audit-fixer per cluster)

Sort cluster theo severity cao nhất giảm dần. Spawn agent `audit-fixer` per cluster —
cluster disjoint file được chạy song song; cluster chạm cùng file chạy tuần tự. Prompt
mỗi agent: finding records đầy đủ + rule files được cite trong Impact + `verifyNote` +
cấm scope expansion. Agent type chưa đăng ký trong session → dùng `general-purpose` và
nhồi đủ contract của `audit-fixer` (mission, rule source, execution loop, output) vào prompt.

Agent trả verdict per finding: `fixed` / `blocked` (+lý do) / `stale` (code đã đổi so với
report, quote không còn khớp) / `needs-decision` (+trade-off 1 câu).

## Step 4 — Verify per batch

1. Compile check theo `verifyNote`. Fail → đưa error về đúng agent sửa trong scope batch,
   tối đa 2 vòng; vẫn fail → STOP, báo user kèm error + files changed, không tick finding
   nào của batch.
2. Orchestrator ĐỘC LẬP re-run Evidence formula của TỪNG finding verdict `fixed` (không
   tin verdict suông): formula còn hit tại site trong hit list → hạ về `blocked`.
3. `stale` / `needs-decision` → gom lại AskUserQuestion cuối run (fix lại theo quyết định
   user, hoặc ghi Triage defer).

## Step 5 — Update report + summary

1. Tick `- [x]` cho finding verified-fixed. Append/update section `## Triage` cuối report:
   mỗi finding một dòng `F-NNN — fixed|spec-fix|deferred|blocked — <files changed | lý do>`.
2. spec-fix cluster → liệt kê để user chạy `/ndv-sync`; không tự chạy trong run này trừ
   khi user yêu cầu.
3. Chat summary theo ngôn ngữ làm việc của project: tally (parsed = fixed + spec-fix +
   deferred + blocked + stale + needs-decision), files changed, compile status. Recommend:
   commit → re-audit đúng loại (`/ndv-audit-code changes vs-<base>` / `/ndv-audit-standards
   changes vs-<base>` / `/ndv-audit-module <module>`) để close loop — prior-report
   re-verify của audit sẽ re-attack các finding đã tick.
