---
name: ndv-audit-fix
description: "Fix-flow đóng vòng audit của kit: parse findings unchecked từ report của /ndv-audit-code, triage per cluster (code-fix / spec-fix → /ndv-specify / register-fix → /ndv-module-matrix / defer), execute code-fix qua agent audit-fixer đúng Fix before→after, verify compile theo verifyNote + orchestrator re-run Evidence formula, tick checkbox + ghi Triage vào report. Never commit. Dùng sau khi có audit report."
argument-hint: "[<report-path> | latest [code | module <module-id>]] [--ids F-001,F-002] [--severity <min>]"
user-invocable: true
allowed-tools: Read, Grep, Glob, Bash, Write, Edit, Task, AskUserQuestion, TodoWrite
---

When this skill is invoked:

## User input

- `<report-path>` — một report `.md` cụ thể (kể cả report legacy của audit skill cũ: cùng
  cấu trúc `## Findings` + `- [ ] **F-NNN**`).
- `latest code` — `.md` mới nhất dưới `<auditReportRoot>/code/**`. `latest module <module-id>`
  — `<auditReportRoot>/<MODULE>-*.md` mới nhất theo frontmatter `date` (bỏ qua `onboard-*.md`).
- `--ids F-001,F-002` — chỉ các finding id này (validate tồn tại + unchecked).
- `--severity <min>` — lọc theo tập đóng R7 (vd `--severity high` = blocker + critical + high).
- Không argument → AskUserQuestion chọn report. KHÔNG tự chọn.

## Non-negotiables (phần của orchestrator)

- **Skip set cố định**: `## Refuted`, `## Notes`, finding đã `- [x]`. Finding flag `unstable`
  hoặc thiếu `Fix (before → after)` → KHÔNG auto-fix, gom vào nhóm needs-decision hỏi user.
- **`## Rule conflicts — needs decision` (C-NNN) không bao giờ auto-fix** — luôn
  AskUserQuestion; user chưa quyết → giữ nguyên.
- **Verify hai tầng per batch**: compile theo `verifyNote` + orchestrator ĐỘC LẬP re-run
  Evidence formula per finding — còn hit tại site đã fix = finding chưa chết, KHÔNG tick.
- **Report update tối thiểu**: tick `- [x]` + append/update `## Triage` — không xóa/rename/
  reorder section nào khác.
- **Never commit.** Scope fix (không drive-by, không sweep sibling-site — vòng audit sau own
  việc đó qua prior-findings re-verify) là contract của agent `audit-fixer`, không restate ở đây.

## Step 0 — Config + resolve report

Read `.claude/ndvkit/ndvkit.config.json` (`auditReportRoot`, `verifyNote`, `specsRoot`,
`matrixRoot`). Resolve report theo user input; đọc frontmatter (`job`, `mode`, `module`,
`verdict`).

## Step 1 — Parse findings

Extract mọi finding unchecked trong `## Findings`, giữ nguyên record (id · severity · Finding
· Evidence + quote · Impact · Fix before→after). Apply `--ids` / `--severity`. Đối chiếu tổng:
số finding parse được = số `- [ ]` trong section — chênh = parse sót, sửa trước khi tiếp tục.

## Step 2 — Triage gate

Cluster findings theo file-cluster + lens. AskUserQuestion per cluster (>4 cluster → gộp câu
hỏi theo nhóm severity):

- **code-fix** — mặc định cho finding có Fix rõ, code sai rules/spec.
- **spec-fix** — code đúng, spec sai (drift) → KHÔNG sửa code; ghi Triage; owner =
  `/ndv-specify <MODULE> --from-audit <report>` (MODULE = module sở hữu file theo `paths`
  trong modules.json). Rule-doc staleness (rule nói A, code reality B) → sửa rule là quyết
  định của rule owner: ghi Triage `spec-fix — rule: <file>`, không tự sửa rule.
- **register-fix** — finding `register-lag` → `/ndv-module-matrix <MODULE>`; không đổi code/spec.
- **defer** — ghi Triage kèm lý do của user, không tick.

`--ids` = user đã pre-triage code-fix cho các id đó — vẫn hỏi lại khi finding là rule-doc
staleness / spec↔code conflict (bản chất là spec-fix candidate).

## Step 3 — Execute (agent audit-fixer per cluster)

Sort cluster theo severity cao nhất giảm dần. Spawn `audit-fixer` per cluster — cluster
disjoint file chạy song song; cluster chạm cùng file → gộp vào MỘT agent, chạy tuần tự trong
agent đó. Prompt: finding records đầy đủ + path rule file được cite trong Impact +
`verifyNote`. Agent type chưa đăng ký → `general-purpose` + dòng đầu prompt: "Read
`.claude/ndvkit/agents/audit-fixer.md` và làm đúng contract trong đó".

Agent trả verdict per finding: `fixed` / `blocked` (+lý do) / `stale` / `needs-decision`
(+trade-off 1 câu).

## Step 4 — Verify per batch

1. Compile check theo `verifyNote`. Fail → RESUME đúng agent instance đã sửa batch đó (giữ
   context — spawn mới chỉ khi harness không resume được) kèm error, tối đa 2 vòng; vẫn fail →
   STOP, báo user kèm error + files changed, không tick finding nào của batch.
2. Orchestrator re-run Evidence formula của TỪNG finding verdict `fixed`: còn hit tại site
   trong hit list → hạ về `blocked`.
3. `stale` / `needs-decision` → gom lại AskUserQuestion cuối run; quyết định fix → resume
   agent của cluster đó.

## Step 5 — Update report + summary

1. Tick `- [x]` cho finding verified-fixed. Append/update `## Triage` cuối report: mỗi finding
   một dòng `F-NNN — fixed|spec-fix|register-fix|deferred|blocked — <files changed | lý do>`.
2. spec-fix / register-fix → liệt kê lệnh để user chạy; không tự chạy trong run này trừ khi
   user yêu cầu.
3. Chat summary: tally (parsed = fixed + spec-fix + register-fix + deferred + blocked + stale
   + needs-decision), files changed, compile status. Recommend: commit → re-audit cùng scope
   (`/ndv-audit-code changes vs-<base>` hoặc `/ndv-audit-code module <MODULE>`) — prior-findings
   re-verify của audit sẽ re-attack các finding đã tick; report mode `module` → re-audit đó
   cũng re-derive `status`.
