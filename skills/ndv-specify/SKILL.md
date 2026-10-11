---
name: ndv-specify
description: "SDD specify single-module của ndvkit: tạo/refresh <specsRoot>/<MODULE>/specify.md cho MỘT module ngoài luồng chính /ndv-gdd-to-spec — clarification đã defer, requirement.md sửa ngoài workflow, spec-fix từ audit (--from-audit), contract back-propagation. Resolve ambiguity qua AskUserQuestion (answer ghi ngược vào requirement.md, cite dạng decision:); specify.md hợp lệ khi zero NEEDS CLARIFICATION. Dùng khi requirement đổi, còn clarification chờ, có contract-gap, hoặc audit kết luận code đúng, spec sai."
argument-hint: "<module-id> [--from-audit <report-path> [--ids F-001,F-002]]"
user-invocable: true
allowed-tools: Read, Glob, Grep, Write, Edit, Task, AskUserQuestion, TodoWrite
---

When this skill is invoked:

## Phase 0 — Config & rules

Read `.claude/ndvkit/ndvkit.config.json` (`gddRoot`, `specsRoot`, `matrixRoot`, `templates`).
Skill này chạy inline nên orchestrator tự áp rules: host `.claude/rules/**` + `CLAUDE.md` ưu
tiên; domain host không define → kit default rules tại `.claude/ndvkit/rules/**`.

## Phase 1 — Load

1. Resolve `<module-id>`; read `<specsRoot>/<MODULE>/requirement.md` (missing → fail, point at
   `/ndv-gdd-to-spec`).
2. Read existing `specify.md` if present (update mode: only requirements whose requirement.md
   source changed are reworked; IDs are stable — never renumber).
3. `--from-audit <report-path>`: đọc các finding được `## Triage` của report đánh `spec-fix`
   (giới hạn bởi `--ids`) thuộc module này — mỗi finding là một **spec-fix candidate** cho
   Phase 2 ("code đúng, spec sai"). Report chưa có Triage → dùng đúng các id trong `--ids`.

## Phase 2 — Clarification loop

1. Collect: mọi marker `NEEDS CLARIFICATION`; mọi requirement ambiguous theo chuẩn EARS
   (missing trigger, unmeasurable response, hidden multi-behavior, undefined term); mọi
   spec-fix candidate.
2. AskUserQuestion in batches (max 4 per call) with concrete options where the GDD constrains
   the answer (cite the GDD anchor in the option description). Spec-fix candidate có đúng 3
   option: (a) behaviour của code là chủ đích → viết lại FR theo as-built (value cite symbol đã
   mở trong session, R3); (b) spec mới là chủ đích → finding quay về code-fix
   (`/ndv-audit-fix`), spec giữ nguyên; (c) GDD nói khác code → quyết định thượng nguồn: không
   sửa FR ở đây, route `/ndv-gdd-to-spec <Feature> --update` sau khi Design sửa GDD
   (`<Feature>` theo frontmatter `gdd-sources` của requirement.md; legacy chỉ có `tdd-source` →
   feature trong path đó `<tddRoot>/<Feature>/…`; `gdd-sources: []` (as-built) → AskUserQuestion
   GDD file nào nói khác code — không đoán feature).
3. Write-back (A→B thay thế, không append, không footnote) vào CẢ HAI tầng:
   - `requirement.md`: theo spec-writer §Mode compose-specify bước 1 — answer thay marker, xóa
     mục khỏi `## Open clarifications`, `Source` thêm form `+ decision:` — marker không sống
     sót để bị hỏi lại lần sau;
   - nội dung specify.md ở Phase 3.
   Answer mâu thuẫn một literal của GDD → không ghi; xử lý như option (c).

## Phase 3 — Compose specify.md (chưa ghi file)

Compose inline theo spec-writer §Mode compose-specify bước 2
(`.claude/ndvkit/agents/spec-writer.md` — SoT composition rules) +
`<templates>/specify-template.md`; skill không restate rules đó.

## Phase 4 — Gate check → write

1. Gate theo §Mode compose-specify bước 3: zero `NEEDS CLARIFICATION` remaining, every FR has
   ≥1 measurable acceptance criterion — else specify.md is NOT written (write-back của Phase 2
   vào requirement.md vẫn giữ); report what is still open instead.
2. **Contract back-propagation**: for every Contract surface row, Grep the `Owner FR` id in
   `<specsRoot>/<Owning module>/requirement.md` (exact ID match — not a symbol/keyword search);
   same for every Consumer obligations row against the consumer's requirement.md. No id, id
   not found, or module absent from `<matrixRoot>/modules.json` → `contract-gap`. Per gap
   AskUserQuestion (batch ≤4 per call): (a) add the FR to the target module (the owning module
   for a Contract surface row, the consumer for a Consumer obligations row); (b) deliberate
   stopgap — record the need under `Out of scope` of the target module's requirement.md (same
   target as (a)) and mark the row `stopgap — <Target> Out of scope`; (c) withdraw the need —
   remove the row and rework the FR text that depended on it (back to Phase 2 for that FR).
   Mọi gap chọn (a) / (b): gom theo TARGET module → MỘT lần spawn `spec-writer` (Task tool,
   model: sonnet) **Mode back-propagation** per target, nhận tất cả row `add` / `stopgap` của
   target đó; ghi các ID trả về vào row, row stopgap thành `stopgap — <Target> Out of scope`.
   Option (a) changes the target's requirement.md, so its specify/plan/tasks become stale —
   name `/ndv-specify <Target>` as a required follow-up.
3. Write specify.md (contract-gap còn mở không chặn việc ghi).
4. Report: requirement count, changed IDs, path, `decision:` cites đã thêm, open
   `contract-gap` list + follow-ups per target module; spec-fix candidates: per id kết quả
   (a)/(b)/(c). Contract surface row đã withdraw (bước 2 (c)) → `/ndv-module-matrix` (full) là
   follow-up bắt buộc (`plannedDeps` consumer → owner trong modules.json stale). FR đã đổi text
   sau khi plan approved → `/ndv-plan <MODULE>` (re-approve).
   Next: `/ndv-plan <MODULE>`.
