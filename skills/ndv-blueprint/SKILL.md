---
name: ndv-blueprint
description: "Bước 0 pipeline ndvkit (architecture): GDD folder → phân tích system design → đề xuất module → <matrixRoot>/blueprint.json + blueprint.html (module blueprint: band Foundation tái dùng cross-project ở trên cùng → Layer 1..n, band core loop, edge consumer → owner). Gate: user chốt decision + approve report trước khi /ndv-gdd-to-spec viết requirement.md. Idempotent: GDD đổi = --update."
argument-hint: "[<gdd-folder>] [--update]"
user-invocable: true
allowed-tools: Read, Glob, Grep, Bash, Write, Edit, Task, AskUserQuestion, TodoWrite
---

When this skill is invoked:

Skill own report kiến trúc module của project, chạy TRƯỚC spec. Protocol tác giả + reviewer sống
trong `module-architect` (§Mode blueprint, §Mode blueprint-review; schema ở §Artifact
blueprint.json); luật thiết kế là `<kitRulesRoot>/Shared/module-design.md` (MD-01…MD-25); check /
render / approve do `scripts/ndv_blueprint.py` cạnh file này (deterministic, không tốn agent). Skill
không restate các protocol đó.

## Thuật ngữ

Định nghĩa duy nhất — report, MD rules và downstream dùng đúng nghĩa này:

- **band** — `foundation`: module tái dùng được ở project khác (đủ 6 tiêu chí MD-18) | `game`.
- **Layer k** — module band `game`: 1 + max Layer của module `game` nó depend (dep vào Foundation
  tính 0). Band Foundation chia row theo dep nội bộ Foundation. KHÁC field `layer` của modules.json
  (topological trên toàn graph, `module-architect` §Layering rules) — hai số không thay thế nhau.
- **buildMode** — `new` | `extend` | `rebuild` | `existing`; khác `new` bắt buộc `extends` code cite (MD-21).
- **role** — `composition` (composition root, MD-16) | `presentation` (UI feature home, MD-22).

## Phase 0 — Config & preflight

1. Read `.claude/ndvkit/ndvkit.config.json` → `gddRoot`, `matrixRoot`, `specsRoot`, `codeRoots`,
   `templates`, `rulesRoot`, `kitRulesRoot` (vắng → `.claude/rules`, `.claude/ndvkit/rules`).
2. `.claude/agents/module-architect.md` phải có §Mode blueprint — else STOP, chỉ README
   §Activation (agent là bản COPY, phải copy lại).
3. `bp` = `<matrixRoot>/blueprint.json`; `script` = `python3
   .claude/ndvkit/skills/ndv-blueprint/scripts/ndv_blueprint.py` (Windows: `python` / `py -3`),
   chạy từ repo root. Không có Python → STOP: cycle / band / cite check và render là điều kiện của
   gate, không làm tay.
4. Model: author `opus`, reviewer `fable` (README §Model routing). Host override (prefix `[model]`
   của user, rule model trong `CLAUDE.md` — kể cả `~/.claude/CLAUDE.md`) thắng.

## Parse arguments

- `<gdd-folder>` — mặc định `<gddRoot>`. Không tồn tại → fail rõ, không bịa GDD. Nằm ngoài
  `<gddRoot>` → AskUserQuestion: sửa `gddRoot` trong config thành folder này (`/ndv-gdd-to-spec` và
  doc-cite chỉ nhận cite dưới `gddRoot`) / chạy tiếp (script báo `outside-gddRoot`).
- `gddFiles` = Glob `<gdd-folder>/**/*.md`, bỏ folder bắt đầu bằng `_` (vd `_work/` của
  gdd-forge). Rỗng → fail.
- `--update`, hoặc `bp` đã tồn tại → `mode: update`; còn lại `create`.

## Phase 1 — Scout (inline, rẻ)

1. Per GDD file: Grep `^#{1,3} ` (kèm số dòng) + đếm dòng → `outline`. KHÔNG đọc body (architect đọc).
2. `script --code-graph --json` → `codeGraph` (SCC theo type-reference dưới `codeRoots`).
   `allFiles: 0` → `codeGraph: none` (greenfield); `allFiles > 0` mà `files: 0` (stack script chưa
   hỗ trợ, hoặc chỉ có asset) → `codeGraph: unavailable` — architect tự đọc code, MD-25 không được
   script kiểm, report ghi rõ.
3. `existing` = id có entry `<matrixRoot>/modules.json` hoặc folder `<specsRoot>/<ID>/` — frozen.
4. Update mode: copy `bp` sang thư mục tạm (`mktemp -d`) làm `baseline` để report diff.

## Phase 2 — Author

Spawn `module-architect` (Task, model của Phase 0 bước 4) **Mode blueprint**. Prompt chỉ mang: mode
· `bp` · gdd folder + `gddFiles` + `outline` · `codeGraph` · `existing` · `date` (hôm nay
`yyyy-mm-dd`) · `create`/`update`. Agent ghi `bp`, trả `{modules, openDecisions, findings}`.

## Phase 3 — Check loop

`script --check --json`. Finding blocking mà `gateOnly: false` → resume CHÍNH instance author với
output script (fix round), tối đa 2 vòng; còn → STOP: report Finding/Evidence/Impact, không review,
không gate. `gateOnly: true` (chỉ còn `approval-void` — nội dung đổi sau approve — và / hoặc
`matrix-band-violation` — modules.json lệch band, author không sửa được) → sang Phase 4; hai kind
này hỏi ở Gate.

## Phase 4 — Review

Spawn instance `module-architect` MỚI **Mode blueprint-review** (read-only, độc lập với author —
hai vai của một agent, như FINDER/VERIFIER của `code-auditor`). Defect → resume author (fix round;
author được dispute kèm evidence) → Phase 3. Tối đa 2 vòng review; vòng 2 chỉ nhận delta. Defect
còn mở hoặc bị dispute → mang sang Gate.

## Phase 5 — Render

`script --render` → `<matrixRoot>/blueprint.html` (từ `<templates>/blueprint-template.html`; bảng
Checks trong HTML = warning của script). Báo path cho user mở trước khi trả lời gate (macOS: `open
<path>`).

## Gate (AskUserQuestion, batch ≤4 câu per call)

Hỏi theo thứ tự — batch trước đổi tập module nên đi trước:

1. Decision `project` (ownership code legacy, assembly strategy, module shape của host) +
   `matrix-band-violation`: đổi band trong blueprint (resume author) / sửa phía spec / matrix
   (`/ndv-specify <MODULE>`, `/ndv-module-matrix`) — chọn hướng này thì lượt gate dừng ở đây, không
   approve; report rồi user chạy lại `/ndv-blueprint` sau khi sửa.
2. Decision `foundation` (admission, mechanism + binding — MD-18, MD-19).
3. Decision `boundary` (split / merge so với bảng system của GDD, ranh giới thật).
4. Decision `gdd-gap` (GDD im lặng / mâu thuẫn chặn ranh giới).
5. Defect review còn mở: sửa theo `fix` của reviewer / giữ nguyên (lý do) / phương án khác.
6. Warning của script (kể cả `scc-decided`, `inexact-anchor`), một câu per kind: sửa / ghi thành
   decision / bỏ qua (→ skill thêm
   `{kind, where, answer}` vào `dismissed[]` của `bp`; script không báo lại).
7. "Approve module blueprint?" — Approve / Revise (ghi rõ sửa gì). CHỈ hỏi ở lượt gate không thu
   answer nào cho bước 1–6; lượt có answer → resume, render lại, lượt sau mới hỏi Approve kèm diff
   so với lượt trước — user luôn approve đúng nội dung đã thấy.

Ghi answer: skill Edit `bp` — `chosen` = label đã chọn (Other → label do user đặt), `answer` =
`decision: <date> — "<answer literal ≤2 câu>"` (R3). Answer mâu thuẫn literal của GDD → KHÔNG ghi
(R3): báo Design sửa GDD rồi `/ndv-blueprint --update`. Answer cần file host (host rule override,
config delta) → in bản nháp, chỉ ghi khi user trả lời "apply". Gom MỌI answer rồi resume author MỘT
lần (Mode blueprint, kèm answers) → Phase 3 → Phase 5; tối đa 2 lượt gate có answer (lượt chỉ hỏi
Approve không tính; Revise ở câu 7 = một lượt có answer), quá → report và dừng.

Approve → `script --approve <date>` (từ chối khi còn blocking hoặc decision mở; ghi `approved`,
`approvedDate`, `approvedDigest`) → `script --render`. Sửa nội dung `bp` sau approve → script báo
`approval-void` (blocking) cho tới khi gate chạy lại. Không bao giờ tự set approval khi chưa có answer.

## Phase 6 — Report

- Band / Layer → modules (`script --check --json` → `modules`; buildMode, role), decision đã chốt, defect còn lại, warning còn lại (kể cả
  `dismissed`), path `blueprint.json` + `blueprint.html`.
- Update mode: diff với `baseline` — module thêm / bỏ / đổi band, edge đổi. Module bị bỏ mà còn
  `<specsRoot>/<ID>/` hoặc entry modules.json → báo, không xóa artifact downstream. Xóa `baseline`.
- Next: `/ndv-gdd-to-spec <blueprint-path>` — skill hỏi phạm vi layer rồi viết spec lần lượt từng
  layer (mapping bám blueprint; GDD của run mặc định = `gddSources`; chạy từng file làm module
  Foundation bị extend lặp và owner chưa đăng ký thành `contract-gap`) → `/ndv-plan` → `/ndv-tasks` →
  `/ndv-implement`. Không commit.
