---
name: ndv-specify
description: "Bước 4a pipeline ndvkit (SDD specify): từ <specsRoot>/<MODULE>/requirement.md tạo/refresh specify.md — EARS requirements đã clarified + acceptance criteria Given/When/Then. Resolve mọi ambiguity qua AskUserQuestion (answer ghi ngược vào requirement.md, cite dạng decision:); specify.md hợp lệ khi zero NEEDS CLARIFICATION. Cũng là owner của spec-fix từ audit (--from-audit). Dùng khi requirement mới/đổi hoặc audit kết luận code đúng, spec sai."
argument-hint: "<module-id> [--from-audit <report-path> [--ids F-001,F-002]]"
user-invocable: true
allowed-tools: Read, Glob, Grep, Write, Edit, Task, AskUserQuestion, TodoWrite
---

When this skill is invoked:

## Phase 0 — Config & rules

Read `.claude/ndvkit/ndvkit.config.json` (`specsRoot`, `matrixRoot`, `templates`). Skill này
chạy inline nên orchestrator tự áp rules: host `.claude/rules/**` + `CLAUDE.md` ưu tiên;
domain host không define → kit default rules tại `.claude/ndvkit/rules/**`.

## Phase 1 — Load

1. Resolve `<module-id>`; read `<specsRoot>/<MODULE>/requirement.md` (missing → fail, point at
   `/ndv-tdd-to-spec`).
2. Read existing `specify.md` if present (update mode: only requirements whose requirement.md
   source changed are reworked; IDs are stable — never renumber).
3. `--from-audit <report-path>`: đọc các finding được `## Triage` của report đánh `spec-fix`
   (giới hạn bởi `--ids`) thuộc module này — mỗi finding là một **spec-fix candidate** cho
   Phase 2 ("code đúng, spec sai"). Report chưa có Triage → dùng đúng các id trong `--ids`.

## Phase 2 — Clarification loop

1. Collect: mọi marker `NEEDS CLARIFICATION`; mọi requirement ambiguous theo chuẩn EARS
   (missing trigger, unmeasurable response, hidden multi-behavior, undefined term); mọi
   spec-fix candidate.
2. AskUserQuestion in batches (max 4 per call) with concrete options where the TDD/GDD
   constrains the answer (cite the source in the option description). Spec-fix candidate có
   đúng 3 option: (a) behaviour của code là chủ đích → viết lại FR theo as-built (value cite
   symbol đã mở trong session, R3); (b) spec mới là chủ đích → finding quay về code-fix
   (`/ndv-audit-fix`), spec giữ nguyên; (c) TDD/GDD nói khác code → quyết định thượng nguồn:
   không sửa FR ở đây, route `/ndv-gdd-to-tdd <Feature> --update` sau khi Design sửa GDD.
3. Write-back (A→B thay thế, không append, không footnote) vào CẢ HAI tầng:
   - `requirement.md`: answer thay marker thành requirement text, xóa mục tương ứng khỏi
     `## Open clarifications` — marker không sống sót để bị hỏi lại lần sau;
   - nội dung specify.md ở Phase 3.
   Thượng nguồn im lặng → `Source`/`Trace` của FR thêm cite
   `decision: <yyyy-mm-dd> — "<literal answer ≤2 câu>"` (R3). Answer mâu thuẫn một literal
   của TDD/GDD → không ghi; xử lý như option (c).

## Phase 3 — Compose specify.md (chưa ghi file)

Fill `<templates>/specify-template.md`:
- final EARS requirements (clarified),
- per-requirement acceptance criteria `Given/When/Then` — measurable; numeric representation
  theo convention của host rules (nếu có), không ambiguous quantifier (R5),
- scope boundary (in/out) + contract surface (what other modules must provide — each row
  carries `Owner FR`) + consumer obligations (what this module requires consumers to do — each
  row carries `Consumer FR`),
- traceability table: requirement ID → TDD section → GDD anchor (hoặc `decision:` cite).

## Phase 4 — Gate check → write

1. Zero `NEEDS CLARIFICATION` remaining — else specify.md is NOT written (write-back của Phase
   2 vào requirement.md vẫn giữ); report what is still open instead.
2. Every FR has ≥1 acceptance criterion.
3. **Contract back-propagation**: for every Contract surface row, Grep the `Owner FR` id in
   `<specsRoot>/<Owning module>/requirement.md` (exact ID match — not a symbol/keyword search);
   same for every Consumer obligations row against the consumer's requirement.md. No id, id
   not found, or module absent from `<matrixRoot>/modules.json` → `contract-gap`. Per gap
   AskUserQuestion (batch ≤4 per call): (a) add the FR to the target module (the owning module
   for a Contract surface row, the consumer for a Consumer obligations row); (b) deliberate
   stopgap — record the need under `Out of scope` of the owning module's requirement.md and
   mark the row `stopgap — <Owner> Out of scope`; (c) withdraw the need — remove the row and
   rework the FR text that depended on it (back to Phase 2 for that FR).
   Mọi gap chọn (a): gom theo TARGET module → MỘT lần spawn `spec-writer` (Task, contract
   back-propagation mode) per target, nhận tất cả row của target đó; ghi các ID trả về vào row.
   Option (a) changes the target's requirement.md, so its specify/plan/tasks become stale —
   name `/ndv-specify <Target>` as a required follow-up.
4. Write specify.md (contract-gap còn mở không chặn việc ghi).
5. Report: requirement count, changed IDs, path, `decision:` cites đã thêm, open
   `contract-gap` list + follow-ups per target module; spec-fix candidates: per id kết quả
   (a)/(b)/(c). FR đã đổi text sau khi plan approved → `/ndv-plan <MODULE>` (re-approve).
   Next: `/ndv-plan <MODULE>`.
