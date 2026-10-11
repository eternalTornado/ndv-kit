---
module: <MODULE>              # id khớp <matrixRoot>/modules.json
gdd-sources:                  # mọi file GDD mà một FR/NFR của module này cite (một module có thể phục vụ nhiều feature)
  - <gddRoot>/<path.md>
created: <yyyy-mm-dd>
updated: <yyyy-mm-dd>
origin: reverse-engineered    # CHỈ as-built (/ndv-onboard reverse-doc) — bỏ khi hết row cite code ∧ Drift vs GDD rỗng
code-source: <module path>    # CHỈ as-built — `paths` của module trong modules.json; bỏ cùng `origin`
---

# Requirements — <MODULE>

> EARS format. Mỗi requirement: đúng MỘT pattern, đúng MỘT behavior testable,
> ID stable (không renumber), Source cite về GDD anchor. Giá trị đo được theo numeric
> convention của host rules, literal quote (R4). Gap = `NEEDS CLARIFICATION` ngay tại
> requirement đó. Flow / state / edge case của GDD thành FR dạng WHEN / WHILE / IF-THEN;
> module mapping sống ở `<matrixRoot>/modules.json`, không ở file này.
>
> **Source** (R3) — một trong các form:
>
> - `<gddRoot>/<path>.md#<section>` — "<literal quote ≤2 câu>"
> - `<gddRoot>/<path>.md#<section>` + `decision: <yyyy-mm-dd>` — "<literal answer ≤2 câu>" —
>   câu trả lời cho GDD gap, luôn kèm GDD anchor của câu hỏi (update pass biết feature nào own);
>   `decision:` đứng một mình chỉ khi không có GDD context (vd intent as-built).
> - `contract: <specsRoot>/<Module>/<file>#<section> — "<row>"` — FR back-propagated từ row
>   Contract surface / Consumer obligations của module khác (`<file>` = specify.md của module chứa
>   row, hoặc requirement.md khi module đó chưa có specify.md); kèm cite GDD khi GDD có nêu need.
>   Forward pass từ GDD không xóa và không ghi đè FR này.
> - as-built: `<path>::<Type>.<Member>` — symbol của file đã mở trong session.

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
- **Source**: `<gddRoot>/<path>.md#<section>` — "<literal quote ≤2 câu>"

### <MODULE>-FR-002

- **Requirement**: …
- **Source**: …

## Non-functional requirements

### <MODULE>-NFR-001

- **Requirement**: The <module> shall <perf/alloc/determinism constraint — đo được>.
- **Source**: <GDD cite hoặc cite rule host tương ứng>

## Data & constants

Entity/field, formula, constant, ID allocation mà các FR trên dùng — literal quote từng giá trị
(R4), numeric representation theo convention host rules (vd integer-only/permille) nếu có. Field
của entity: `Name` = `<Entity>.<Field>`, cột Value ghi type + constraint literal. ID allocation:
cite id plan/allocation scheme của host, chỉ ghi id/range MỚI module này cần cấp. As-built: cột
Source = code symbol. Không có → `N/A — <lý do>`.

| Name | Value / formula (literal) | Source (GDD cite) | FR |
|---|---|---|---|

## Contract surface

Những gì module này CẦN từ module khác để thỏa các FR trên — không absorb vào own scope.
`Owner FR` = ID FR/NFR trong `<specsRoot>/<Owning module>/requirement.md` cấp need này (Grep ID khớp,
không bịa ID); chưa có → ghi `contract-gap`. Stopgap có chủ đích: `stopgap — <Owning module> Out of
scope`. `/ndv-gdd-to-spec` gate B hoặc `/ndv-specify` Phase 4 đóng gap.

| Cần | Owning module | Dạng | Owner FR | FR liên quan |
|---|---|---|---|---|

## Consumer obligations

Những gì module này BUỘC module tiêu thụ phải làm để contract đúng (vd gọi validate trước khi đọc giá
trị) — chiều ngược của Contract surface. `Consumer FR` = ID trong requirement.md của consumer; chưa có →
`contract-gap`. Stopgap có chủ đích: `stopgap — <Consumer module> Out of scope`. Không có nghĩa vụ
nào → `N/A`.

| Nghĩa vụ | Consumer module | Consumer FR | FR nguồn |
|---|---|---|---|

## Out of scope

<Phần GDD / responsibility cố tình KHÔNG thuộc module này + module nào nhận thay (cite GDD anchor).
Stopgap có chủ đích mà module này là target (owning module của need Contract surface, consumer của
nghĩa vụ Consumer obligations) cũng ghi ở đây.>

## Drift vs GDD

<CHỈ artifact `origin: reverse-engineered` — bỏ cùng `origin` khi không còn row nào cite code ∧
section rỗng (spec-writer §Mode forward). Mỗi chỗ code lệch GDD cover feature: Finding / Evidence
(symbol code + GDD cite, literal quote) / Impact (R7), không chọn bên. GDD không cover feature →
`N/A — <lý do>`.>

## Open clarifications

<List `NEEDS CLARIFICATION`. Marker còn lại sau `/ndv-gdd-to-spec` (GDD gap user chọn Defer, gap
chưa được trả lời) → `/ndv-specify` resolve qua AskUserQuestion; specify.md chỉ được ghi khi list
rỗng.>
