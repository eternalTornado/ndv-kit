---
module: <MODULE>              # id khớp <matrixRoot>/modules.json
tdd-source: <tddRoot>/<Feature>/tdd.md
created: <yyyy-mm-dd>
updated: <yyyy-mm-dd>
---

# Requirements — <MODULE>

> EARS format. Mỗi requirement: đúng MỘT pattern, đúng MỘT behavior testable,
> ID stable (không renumber), cite về TDD section. Giá trị đo được theo numeric
> convention của host rules. Gap = `NEEDS CLARIFICATION` ngay tại requirement đó.
>
> FR back-propagated từ Contract surface của module tiêu thụ dùng Source dạng
> `contract: <specsRoot>/<Consumer>/specify.md#Contract surface — "<row Cần>"` (kèm cite
> TDD/GDD khi TDD có nêu need); forward pass từ TDD không xóa và không ghi đè FR này.

## EARS patterns (chuẩn duy nhất được dùng)

| Pattern | Form |
|---|---|
| Ubiquitous | `The <module> shall <response>.` |
| Event-driven | `WHEN <trigger>, the <module> shall <response>.` |
| State-driven | `WHILE <state>, the <module> shall <response>.` |
| Unwanted behavior | `IF <condition>, THEN the <module> shall <response>.` |
| Optional feature | `WHERE <feature is present>, the <module> shall <response>.` |
| Complex | Kết hợp — tối đa một chuỗi WHEN/WHILE/IF per requirement. |

## Functional requirements

### <MODULE>-FR-001

- **Requirement**: WHEN <trigger>, the <module> shall <response>.
- **Source**: `<tddRoot>/<Feature>/tdd.md#<section>` — "<literal quote ≤2 câu>"

### <MODULE>-FR-002

- **Requirement**: …
- **Source**: …

## Non-functional requirements

### <MODULE>-NFR-001

- **Requirement**: The <module> shall <perf/alloc/determinism constraint — đo được>.
- **Source**: <TDD cite hoặc cite rule host tương ứng>

## Contract surface

Những gì module này CẦN từ module khác để thỏa các FR trên — không absorb vào own scope.
`Owner FR` = ID FR/NFR trong `<specsRoot>/<Owning module>/requirement.md` cấp need này (Grep ID khớp,
không bịa ID); chưa có → ghi `contract-gap`. `/ndv-specify` Phase 4 đóng gap.

| Cần | Owning module | Dạng | Owner FR | FR liên quan |
|---|---|---|---|---|

## Consumer obligations

Những gì module này BUỘC module tiêu thụ phải làm để contract đúng (vd gọi validate trước khi đọc giá
trị) — chiều ngược của Contract surface. `Consumer FR` = ID trong requirement.md của consumer; chưa có →
`contract-gap`. Không có nghĩa vụ nào → `N/A`.

| Nghĩa vụ | Consumer module | Consumer FR | FR nguồn |
|---|---|---|---|

## Out of scope

<Liệt kê phần TDD cố tình KHÔNG thuộc module này + module nào nhận thay.>

## Open clarifications

<List `NEEDS CLARIFICATION`. `/ndv-specify` resolve list này qua AskUserQuestion; specify.md chỉ được ghi khi list rỗng.>
