---
feature: <Feature>            # PascalCase, theo glossary/feature-id scheme của project host nếu có
gdd-sources:                  # mọi file GDD đã đọc để sinh TDD này
  - <gddRoot>/<path.md>
created: <yyyy-mm-dd>
updated: <yyyy-mm-dd>
---

# TDD — <Feature>

> Technical Design Document. Chỉ chứa những gì kỹ thuật cần để implement.
> Mọi constant/formula/enum/edge-case là literal quote kèm cite `<GDD path>#<section>`.
> Gap = `NEEDS CLARIFICATION: <câu hỏi cụ thể>` inline. Không suy diễn "typical game".
> Tham chiếu code có sẵn (as-built) → cite symbol `<path>::<Type>.<Member>` (R3), mở file khi ghi; không `:<line>` đứng một mình.

## 1. Overview kỹ thuật

<2-4 câu: feature làm gì về mặt hệ thống, module nào own, bên nào (client/server/local) quyết cái gì.>

## 2. Data

### 2.1 Entities & fields

| Entity | Field | Type | Constraint | Source (GDD cite) |
|---|---|---|---|---|

### 2.2 ID allocation

<Nếu host rules có id plan/allocation scheme: cite scheme đó, chỉ ghi id/range MỚI
feature này cần cấp. Không có scheme → `N/A — host không quy định id plan`.>

### 2.3 Config vs runtime state

| Datum | Config (static) | Runtime state | Persisted |
|---|---|---|---|

## 3. Formulas & constants

Literal quote từng formula + constant. Numeric representation theo convention
host rules (vd integer-only/permille) nếu có.

| Name | Value / formula (literal) | Source (GDD cite) |
|---|---|---|

## 4. State & lifecycle

<State machine / lifecycle của entity chính. Nếu host rules có trust boundary
(vd server-authoritative), ghi rõ bên nào own mỗi quyết định theo rule đó.>

## 5. Flows

<Mỗi flow: numbered sequence `input → intent → resolution → render`.
Trigger + timing rule literal từ GDD.>

## 6. Contract surface

### 6.1 Cần từ hệ thống khác

| Cần gì | Từ module/system | Dạng (interface/event/wire) |
|---|---|---|

### 6.2 Cung cấp cho hệ thống khác

| Cung cấp gì | Cho ai | Dạng |
|---|---|---|

### 6.3 Wire (nếu có client ↔ server)

<Endpoint/payload shape nếu GDD/BE contract đã định; chưa có → `NEEDS CLARIFICATION`.>

## 7. Edge cases

| # | Condition (literal từ GDD) | Expected behavior | Source |
|---|---|---|---|

## 8. Module mapping đề xuất

| Phần của TDD | Module (id theo scheme của host) | Mới / mở rộng module có sẵn |
|---|---|---|

<Hàng "mở rộng module có sẵn" phải nêu điểm mở rộng bằng symbol `<path>::<Type>.<Member>` đã mở
file trong session; không kế thừa anchor từ TDD cũ mà chưa mở lại.>

## 9. Open clarifications

<Gom mọi `NEEDS CLARIFICATION` inline ở trên thành list để Design trả lời. Rỗng = ghi `N/A — không còn gap`.>
