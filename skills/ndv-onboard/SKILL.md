---
name: ndv-onboard
description: "Onboard kit vào project ĐANG CHẠY GIỮA CHỪNG (brownfield adoption). 3 options chọn được (đơn lẻ hoặc kết hợp): (1) status — inventory artifact coverage + drift bằng script, không tốn agent; (2) matrix — reverse module matrix từ code hiện có (module-architect Mode brownfield); (3) reverse-doc — brownfield implement hiện tại → TDD as-built + requirement as-built (EARS, cite code). Dùng khi mới thêm kit vào repo có sẵn, hoặc muốn đối soát pipeline với thực tế code."
argument-hint: "[status | matrix | reverse-doc [<module-id>...]] (omit = hỏi)"
user-invocable: true
allowed-tools: Read, Glob, Grep, Bash, Write, Edit, Task, AskUserQuestion, TodoWrite
---

When this skill is invoked:

## Phase 0 — Config

1. Read `.claude/ndvkit/ndvkit.config.json`. Rule source + precedence do các agent được spawn
   tự resolve (host `.claude/rules/**` > kit `.claude/ndvkit/rules/**`).
2. **Config bootstrap** (chỉ khi thiếu): `codeRoots` rỗng → detect ứng viên (folder chứa
   source/module code: Glob top-level, nhận diện engine/stack từ file markers — vd
   `Assets/` + `ProjectSettings/` = Unity, `go.mod` = Go, `package.json` = Node) →
   AskUserQuestion confirm rồi ghi vào config. `verifyNote`/`contractsDoc` rỗng → hỏi MỘT
   lần trong cùng câu hỏi (cho phép skip).

## Parse arguments

- `status` → Option 1. `matrix` → Option 2. `reverse-doc [<module-id>...]` → Option 3
  (giới hạn module nếu có args).
- Không có argument → AskUserQuestion (multiSelect): "Onboard project giữa chừng — chạy
  option nào?" (1) Status-check, (2) Generate module matrix, (3) Reverse-doc brownfield →
  TDD + spec. Chọn nhiều → chạy theo thứ tự 1 → 2 → 3 (status nuôi matrix, matrix nuôi
  reverse-doc).

---

## Option 1 — Status-check (READ-ONLY trừ report; không spawn agent)

1. **Inventory + artifact coverage matrix**:
   `python3 .claude/ndvkit/skills/ndv-sync/scripts/ndv_check.py --inventory` (Windows:
   `python` / `py -3`) — estate counts per root + bảng per module
   `Module | Code | Matrix entry | TDD | requirement | specify | plan | tasks | Audit report`
   (`✔ <path>` / `—`), gồm cả folder code chưa đăng ký và spec folder không có matrix entry.
   Module có code nhưng không artifact = brownfield gap; artifact không code = planned/stale.
   Không có Python → dựng cùng bảng đó bằng Glob từng root (mọi ô có path hoặc `—`, không đoán).
2. **Drift** = đúng các check của `/ndv-sync` Phase 1, không làm bản rút gọn riêng:
   `… ndv_check.py --checks doc-cite,code-cite,contract-gap,deps` + `… --refresh-status`
   (dry-run) + check void-approval theo timestamp của `/ndv-sync` Phase 1.
3. Ghi `<auditReportRoot>/onboard-<yyyy-mm-dd>.md` (frontmatter `date`, `job: onboard-status`
   + output hai bước trên + `## Recommended next steps`) và chat summary: tình trạng từng
   tier, gap lớn nhất, route đề xuất — Option 2 nếu chưa có matrix, Option 3 cho module thiếu
   spec, `/ndv-audit-code current` cho estate review sâu, `/ndv-sync` cho drift.

## Option 2 — Generate module matrix (reverse từ code)

Precondition: `codeRoots` đã có (Phase 0). Matrix đã tồn tại → đây là re-sync, không rebuild.

1. Spawn `module-architect` (Task tool) với chỉ thị **Mode brownfield** + `codeRoots` — agent
   tự enumerate module từ code, dựng import graph, tính layer, ghi
   `<matrixRoot>/modules.json` (contract: `module-architect` §Mode brownfield).
2. `… ndv_check.py --refresh-status --write` — derive `status` mọi entry + sinh
   `<matrixRoot>/modules.md`.
3. Validate như `/ndv-module-matrix` Phase 2. Report: layer table, `NON_CONFORMING` (folder
   code ngoài convention), `EXTERNAL`, cycles/drift.

## Option 3 — Reverse-doc: brownfield implement → TDD + spec (as-built)

Precondition: modules.json tồn tại (chạy Option 2 trước nếu chưa — hỏi user). Scope =
`<module-id>...` args, hoặc AskUserQuestion chọn từ coverage matrix (module có code nhưng
thiếu TDD/spec; multiSelect).

Nguyên tắc AS-BUILT (khác chiều forward của pipeline):

- **Code là observed source** — mọi behavior/formula/constant trích từ code cite symbol
  `<path>::<Type>.<Member>`, đặt vào vị trí GDD cite của template (R3). KHÔNG bịa intent:
  WHY không suy ra được → `NEEDS CLARIFICATION: <câu hỏi cho owner>`.
- **GDD đối chiếu nếu có**: code↔GDD lệch = ghi vào section `## Drift vs GDD`
  (Finding/Evidence/Impact), KHÔNG tự nghiêng về bên nào.
- Artifact as-built đánh dấu frontmatter `origin: reverse-engineered` + `code-source:
  <module path>` — downstream (`/ndv-specify` trở đi) đối xử như requirement thường sau
  khi clarifications được owner trả lời.

Per module (spawn parallel khi nhiều module):

1. **TDD as-built**: spawn `tdd-writer` với Mode brownfield (contract trong agent) — target
   `<tddRoot>/<Feature>/tdd.md`, template `<templates>/tdd-template.md`; `gdd-sources`
   frontmatter ghi `N/A — reverse-engineered from code` (hoặc GDD path nếu có đối chiếu).
2. **requirement.md as-built**: spawn `spec-writer` — trích TDD as-built thành EARS
   requirements, Source cite trỏ TDD section (chain về code). Target
   `<specsRoot>/<MODULE>/requirement.md`.
3. Edit entry modules.json: điền `tdd`/`spec` path vừa tạo; rồi
   `… ndv_check.py --refresh-status <MODULE...> --write` (status + `modules.md`).
4. KHÔNG tự sinh specify/plan/tasks trong onboard — đó là forward flow: report list
   `NEEDS CLARIFICATION` + drift, recommend `/ndv-specify <MODULE>` sau khi owner trả lời.

## Close

Tổng kết theo option đã chạy: artifact đã ghi (paths), coverage matrix trước/sau, mọi
`NEEDS CLARIFICATION` + drift finding chờ owner, next steps. Không commit.
