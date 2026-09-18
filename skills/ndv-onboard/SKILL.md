---
name: ndv-onboard
description: "Onboard kit vào project ĐANG CHẠY GIỮA CHỪNG (brownfield adoption). 3 options chọn được (đơn lẻ hoặc kết hợp): (1) status-check — inventory tình trạng project + artifact coverage + gap report; (2) matrix — reverse module matrix từ code hiện có; (3) reverse-doc — brownfield implement hiện tại → TDD as-built + requirement/specify as-built (EARS, cite code). Dùng khi mới thêm kit vào repo có sẵn, hoặc muốn đối soát pipeline với thực tế code."
argument-hint: "[status | matrix | reverse-doc [<module-id>...]] (omit = hỏi)"
user-invocable: true
allowed-tools: Read, Glob, Grep, Bash, Write, Edit, Task, AskUserQuestion, TodoWrite
---

When this skill is invoked:

## Phase 0 — Config & rules

1. Read `.claude/ndvkit/ndvkit.config.json`. Rule source: host `.claude/rules/**` +
   `CLAUDE.md` nếu có; domain nào host không define → dùng kit default rules tại
   `.claude/ndvkit/rules/**`. Host thắng khi mâu thuẫn.
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

## Option 1 — Status-check (READ-ONLY trừ report)

Delegate cho agent `onboarder` (Task tool) nhiệm vụ **SURVEY** — inventory tình trạng
project vs pipeline, evidence-backed (mọi claim có formula/path):

1. **Estate inventory**: host rules có gì (`rulesRoot` glob) · `gddRoot` tồn tại? bao nhiêu
   doc? · `tddRoot`/`matrixRoot`/`specsRoot` tồn tại? artifact nào? · `codeRoots`: đếm
   module folder (theo module convention resolve được từ rules) + tổng source files.
2. **Artifact coverage matrix** — bảng per module (union: code folders ∪ modules.json ∪
   `<specsRoot>/*`):

   | Module | Code | Matrix entry | TDD | requirement | specify | plan | tasks | Audit report |

   Mỗi ô `✔ <path>` / `—`. Module có code nhưng không artifact = brownfield gap; artifact
   không code = planned/stale.
3. **Drift signals** (nhanh, không phải full audit): modules.json `deps[]` vs import/using
   graph thực (sample-check, ghi sample size); plan/tasks `approved` predates specify
   rewrite (void-approval — cơ chế `/ndv-sync` Phase 1); TDD cite GDD anchor còn tồn tại.

Orchestrator nhận kết quả SURVEY → ghi `<auditReportRoot>/onboard-<yyyy-mm-dd>.md`
(frontmatter date/job: onboard-status + các bảng trên + `## Recommended next steps`) và
chat summary: tình trạng từng tier, gap lớn nhất, route đề xuất — thường là Option 2 nếu
chưa có matrix, Option 3 cho module thiếu spec, `/ndv-audit-code`/`/ndv-audit-standards`
cho estate review sâu, `/ndv-sync` cho drift.

## Option 2 — Generate module matrix (reverse từ code)

Precondition: `codeRoots` đã có (Phase 0). Matrix đã tồn tại → đây là re-sync, không rebuild
(update mode của `/ndv-module-matrix`).

1. Spawn `onboarder` (Task tool) nhiệm vụ **DISCOVER**: enumerate module từ CODE (folder
   khớp module convention — composition-root, folder shape; folder không khớp → list
   `NON_CONFORMING`, không silently bỏ), per module {namespace, compositionRoot,
   imports[] từ using/import graph THỰC}, external deps tách riêng.
2. Spawn `module-architect` (Task tool) với output DISCOVER ở chế độ **brownfield**:
   - Dependency lấy từ import graph thực; spec/contract doc nếu có dùng làm đối chiếu —
     lệch nhau là drift finding, code là observed truth.
   - Compute waterfall layers (L0 = không depend module nào; layer = 1 + max(deps));
     cycle = blocking finding + đề xuất interface split, KHÔNG tự resolve.
   - Ghi `<matrixRoot>/modules.json` — module có code: `status: "implemented"`; field
     `tdd`/`spec` chỉ điền khi artifact TỒN TẠI (Option 3 điền dần), không placeholder.
   - Render `<matrixRoot>/index.html` từ `<templates>/module-matrix-template.html`.
3. Validate (như `/ndv-module-matrix` Phase 3): JSON parse, deps tồn tại, layer-N chỉ ref
   layer < N. Report: layer table, module ngoài convention (NON_CONFORMING), cycles/drift.

## Option 3 — Reverse-doc: brownfield implement → TDD + spec (as-built)

Precondition: modules.json tồn tại (chạy Option 2 trước nếu chưa — hỏi user). Scope =
`<module-id>...` args, hoặc AskUserQuestion chọn từ coverage matrix (module có code nhưng
thiếu TDD/spec; multiSelect).

Nguyên tắc AS-BUILT (khác chiều forward của pipeline):

- **Code là observed source** — mọi behavior/formula/constant trích từ code cite
  symbol `<path>::<Type>.<Member>`, đặt vào vị trí GDD cite của template; thêm `:<line>`
  sau symbol chỉ khi cần đúng một dòng, không `path:line` đứng một mình (R3). KHÔNG bịa
  intent: behavior đọc được thì ghi, WHY không suy ra được →
  `NEEDS CLARIFICATION: <câu hỏi cho owner>`.
- **GDD đối chiếu nếu có**: `gddRoot` có doc cover feature → cross-check; code↔GDD lệch =
  ghi vào section `## Drift vs GDD` (Finding/Evidence/Impact), KHÔNG tự nghiêng về bên nào.
- Artifact as-built đánh dấu frontmatter `origin: reverse-engineered` + `code-source:
  <module path>` — downstream (`/ndv-specify` trở đi) đối xử như requirement thường sau
  khi clarifications được owner trả lời.

Per module (spawn parallel khi nhiều module):

1. **TDD as-built**: spawn `tdd-writer` với mode brownfield — đọc module code (+ spec/doc
   rời rạc nếu có), fill `<templates>/tdd-template.md`: data/formulas/state/flows/contract
   surface/edge cases NHƯ CODE ĐANG LÀM, mỗi mục cite symbol `<path>::<Type>.<Member>` theo
   Mode brownfield của agent; `gdd-sources` frontmatter
   ghi `N/A — reverse-engineered from code` (hoặc GDD path nếu có đối chiếu). Target
   `<tddRoot>/<Feature>/tdd.md`.
2. **requirement.md as-built**: spawn `spec-writer` — trích TDD as-built thành EARS
   requirements (`<MODULE>-FR-NNN`), Source cite trỏ TDD section (chain về code). Target
   `<specsRoot>/<MODULE>/requirement.md`.
3. Update modules.json entry: điền `tdd`/`spec` path vừa tạo; re-render matrix
   (`--render-only` logic).
4. KHÔNG tự sinh specify/plan/tasks trong onboard — đó là forward flow: report list
   `NEEDS CLARIFICATION` + drift, recommend `/ndv-specify <MODULE>` sau khi owner trả lời.

## Close

Tổng kết theo option đã chạy: artifact đã ghi (paths), coverage matrix trước/sau, mọi
`NEEDS CLARIFICATION` + drift finding chờ owner, next steps. Không commit.
