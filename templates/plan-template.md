---
module: <MODULE>
specify-source: <specsRoot>/<NNN>_<MODULE>/specify.md
approved: false               # /ndv-plan set true qua AskUserQuestion gate — không tự set
approved-date:
created: <yyyy-mm-dd>
updated: <yyyy-mm-dd>
---

# Plan — <MODULE>

> Technical design HOW cho specify.md, tuân module/coding convention của rule source (host
> `<rulesRoot>` ưu tiên, fallback `<kitRulesRoot>`) — cite rule bằng đúng path của file đã mở
> (R1). Design decision không bị spec ràng buộc: chọn MỘT phương án + justify kèm cite. Không
> timeline/estimate.
> Tham chiếu component/method có sẵn → cite symbol `<path>::<Type>.<Member>` (R3); mọi anchor code trong plan phải do người viết plan mở file trong session, không kế thừa từ specify/requirement.
> Code SẼ BỊ THAY bởi plan này: mô tả ở dạng `trước implement: …` + cite symbol của member chứa
> nó — không `:<line>`, không "currently"/"hiện tại" (câu đó sai ngay sau `/ndv-implement`).

## 1. Module skeleton

```text
<code root>/<Module>/
├── <entry/registration class theo convention host>
└── <folder layout theo convention host — nếu host có closed folder set, chỉ dùng folder được phép>
```

- Namespace/package: <theo convention host>
- Cấu trúc ngoài convention host cho phép: <N/A hoặc liệt kê + lý do + cần user/rule-owner duyệt>

## 2. Types

| Type | Folder | Naming/suffix rule (host) | Trách nhiệm (1 câu) |
|---|---|---|---|

## 3. Data flow per FR

### <MODULE>-FR-001

<Sequence: component nào gọi gì, event nào bắn (naming theo host convention), state đổi ở đâu. Component/method có sẵn → `<path>::<Type>.<Member>`; component mới → tên + folder theo skeleton §1. Component/method sẽ bị thay → `trước implement: …` + symbol (xem header).>

## 3a. State & guards

> Bắt buộc khi service giữ mutable state qua nhiều operation hoặc async flow. Stateless →
> `N/A — stateless` + một câu lý do. Flow §3 gọi guard / transition theo tên ở đây, không viết lại
> điều kiện inline.

**State fields**

| Field | Ý nghĩa | Set ở (transition) | Reset ở (transition) |
|---|---|---|---|

**Invariants**: mệnh đề luôn đúng sau mọi transition (vd `PresentedConflict != null ⇒ _held != null`).
Transition nào reset một field thì reset luôn mọi field mà invariant buộc với nó.

**Guard matrix**: mỗi operation public / trigger × precondition mà spec đòi (signed-in, online,
schema, in-flight…). Ô = tên guard + AC cite, hoặc `N/A` + lý do.

| Operation | <precondition 1> | <precondition 2> | … |
|---|---|---|---|

## 4. Dependency wiring

- Declared dependencies: <list — PHẢI bằng `deps[] ∪ plannedDeps[]` của entry trong `<matrixRoot>/modules.json`; cạnh plan cần mà code chưa có → `plannedDeps` kèm spec evidence, không tự thêm vào `deps`>
- Registration/lifecycle: <theo module convention host — ghi rõ constraint nào của host áp vào đây>

## 5. UI (nếu có)

<Theo UI convention của host: framework, authoring rule, binding pattern, naming, theming.
Không có UI → `N/A`.>

## 6. Serialization & persistence

<Serializer + casing/contract convention theo host rules; persistence mechanism nếu cần.>

## 7. Risks & pitfalls

| Pitfall (rule/pitfalls doc — cite path file đã mở) | Áp dụng thế nào (code giữ/mở rộng → cite symbol; code sẽ bị thay → `trước implement: …` + symbol) | Thiết kế né ra sao |
|---|---|---|

## 8. FR → design element mapping

| FR | Type/method thực hiện | Ghi chú |
|---|---|---|

## 9. Decisions

| Decision | Phương án chọn | Justification + cite |
|---|---|---|
