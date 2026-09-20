---
module: <MODULE>
requirement-source: <specsRoot>/<MODULE>/requirement.md
created: <yyyy-mm-dd>
updated: <yyyy-mm-dd>
---

# Specify — <MODULE>

> requirement.md sau clarification. INVARIANT: zero `NEEDS CLARIFICATION` trong file này.
> ID giữ nguyên từ requirement.md. Mỗi FR có ≥1 acceptance criterion đo được.

## Scope

- **In**: <danh sách behavior module này own>
- **Out**: <behavior thuộc module khác — ghi module nhận>

## Requirements (EARS, clarified)

### <MODULE>-FR-001

- **Requirement**: WHEN <trigger>, the <module> shall <response>.
- **Acceptance criteria**:
  - Given <precondition>, When <action>, Then <observable result — giá trị đo được, numeric convention theo host rules>.
- **Trace**: `<tddRoot>/<Feature>/tdd.md#<section>` ← `<gddRoot>/<path>#<anchor>`

### <MODULE>-FR-002

…

## Non-functional (clarified)

### <MODULE>-NFR-001

- **Requirement**: …
- **Acceptance criteria**: <cách đo — vd zero alloc per-frame verified bằng profiler marker>

## Contract surface (final)

> `Owner FR` = ID trong `<specsRoot>/<Owning module>/requirement.md` (Grep ID khớp). Row chưa có owner FR =
> `contract-gap` — `/ndv-specify` Phase 4 xử lý; gap còn mở phải nêu trong report. Stopgap có chủ đích:
> ghi `stopgap — <Owning module> Out of scope`.

| Cần | Owning module | Interface/Event cụ thể | Owner FR | FR |
|---|---|---|---|---|

## Consumer obligations (final)

> Nghĩa vụ module này đặt lên consumer. `Consumer FR` = ID trong requirement.md của consumer; chưa có →
> `contract-gap`. Không có → `N/A`.

| Nghĩa vụ | Consumer module | Consumer FR | FR nguồn |
|---|---|---|---|

## Traceability

| Requirement | TDD section | GDD anchor |
|---|---|---|
| <MODULE>-FR-001 | … | … |
