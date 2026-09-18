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

| Cần | Owning module | Dạng | FR liên quan |
|---|---|---|---|

## Out of scope

<Liệt kê phần TDD cố tình KHÔNG thuộc module này + module nào nhận thay.>

## Open clarifications

<List `NEEDS CLARIFICATION` — phải rỗng trước khi /ndv-specify chạy.>
