# ndvkit default rules

Bộ rules DEFAULT của kit — dùng khi project host KHÔNG tự define rules riêng.

## Precedence

1. **Host rules thắng**: nếu project có `.claude/rules/**` / `CLAUDE.md` define rule cùng domain,
   rule của host OVERRIDE rule tương ứng trong bộ này (kể cả khi mâu thuẫn trực tiếp).
2. **Kit rules là fallback**: domain nào host im lặng → áp rule trong bộ này.
3. Trong bộ này, khi rule mâu thuẫn nhau: `Shared/` (cross-stack) > stack-specific (`Unity/`, `Server/`).

## Cách dùng

- **Không copy**: agents/skills của kit tự đọc từ `kitRulesRoot` (config) khi cần — host không phải làm gì.
- **Adopt (khuyến nghị cho project mới)**: copy folder này vào `.claude/rules/` của project để
  auto-load mỗi session (file có `paths:` frontmatter chỉ load khi edit file khớp glob).
  Sau khi adopt, project chỉnh sửa bản copy = định nghĩa rules riêng — bản trong kit giữ nguyên làm default.

## 3 nhóm

| Nhóm | Nội dung |
|---|---|
| `Shared/` | Cross-stack: `constitution` (principles + writing + governance), `ai-discipline` (R1–R10 AI behavior), `id-plan` (id allocation invariants), `coding-style`, `performance`, `security`. |
| `Unity/` | Client Unity: `constitution` (engine constraints), `conventions` (naming), `coding-style` (C#), `module-constraints` (world/module/hot-path), `naming-ui-toolkit`, `ui-theming` (reskin/token), `asset-structure`, `security` (trust boundary), `known-pitfalls`. Project không dùng Unity → bỏ qua nhóm này. |
| `Server/` | BE Go/PostgreSQL: `server.md` (structure), `db.md` (schema). Project không có BE hoặc dùng stack khác → bỏ qua. |

## Register documents (KHÔNG nằm trong bộ này)

Feature matrix / module map / project reference là REGISTER per-project (state, không phải rule) —
pipeline ndvkit sinh và maintain chúng tại `<matrixRoot>/modules.json` (+ `index.html`).
Rule chỉ định INVARIANT; register ghi hiện trạng.

## Thêm rule mới

- Cross-stack → `Shared/` (đúng file domain); stack-specific → `Unity/`/`Server/`.
- Rule tự chứa, project-agnostic — KHÔNG chứa tên class/path/asset cụ thể của một project
  (những thứ đó thuộc register/report/host rules).
- Trùng nội dung thì gộp về đúng một home; file khác cite-back, không restate.
