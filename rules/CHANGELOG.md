# Rules changelog

File này là nơi DUY NHẤT ghi amendment cho rules của kit (written rationale + migration note
theo [Shared/constitution.md](Shared/constitution.md) §Governance). Body của rule file chỉ
chứa current state (R9.1).

## 2026-09-18 — R1, R3, R4: cite code theo symbol

- **Rationale**: một lần sửa `GameLose.cs` (dịch dòng, không đổi hành vi) làm sai anchor
  `path:line` ở 3 TDD, 1 requirement.md, 1 plan.md, 1 audit report và modules.json cùng lúc;
  estate có 777 anchor line-based trỏ vào code và không bước nào trong pipeline verify chúng.
  Line number là định danh vỡ khi thêm một dòng trống; symbol chỉ vỡ khi rename — thay đổi
  ngữ nghĩa thật, đáng vỡ.
- **Migration**: anchor `<path>:<line>` vào code đã có trong artifact vẫn đọc được, không
  migrate hàng loạt; chuyển sang symbol khi artifact sở hữu được ghi lại lần kế tiếp (mọi
  skill idempotent). `/ndv-sync` Phase 1 báo `broken-cite` cho anchor không còn khớp.

## 2026-09-18 — Harmonization pass

- **Shared/ai-discipline.md — thêm Audit Evidence carve-out ở R1**: Rationale: report audit
  đọc snapshot tại một commit nên cần cho phép anchor `<path>:<line>` không kèm symbol cho
  file không có symbol (markup, stylesheet, data, asset). Migration: N/A — không có artifact
  phụ thuộc.
- **Shared/ai-discipline.md — sửa ví dụ cite line-only ở R3/R7/R8/R9**: Rationale: các ví dụ
  cite trong R3/R7/R8/R9 vẫn dùng dạng `<path>:<line>` line-only cho code, mâu thuẫn với R1
  sau khi R1 chuyển cite code sang symbol. Migration: N/A — không có artifact phụ thuộc.
- **Shared/ai-discipline.md — thêm severity taxonomy SoT ở R7**: Rationale: R7 định nghĩa
  format finding nhưng chưa chỉ rõ tập severity hợp lệ, để mỗi audit skill tự đặt tên severity
  riêng. Migration: N/A — không có artifact phụ thuộc.
- **Shared/ai-discipline.md — Enforcement liệt kê đủ 3 audit skill**: Rationale: mục
  Enforcement chỉ cite `/ndv-audit-module` trong khi kit đã có thêm `/ndv-audit-code` và
  `/ndv-audit-standards`. Migration: N/A — không có artifact phụ thuộc.
- **Shared/ai-discipline.md — bảng Canonical location index thêm 3 dòng**: Rationale: bảng
  Canonical location index chưa trỏ severity taxonomy, glossary và amendment history về đúng
  SoT của chúng. Migration: N/A — không có artifact phụ thuộc.
- **Shared/coding-style.md — Constants cite theo stack rules**: Rationale: mục Naming
  Conventions ghi cứng `UPPER_SNAKE_CASE` cho constants trong khi `Server/server.md` quy định
  Go dùng MixedCaps, tạo mâu thuẫn giữa Shared và Server. Migration: N/A — không có artifact
  phụ thuộc.
- **Server/server.md — thêm section Naming**: Rationale: `server.md` chưa có mục Naming riêng
  cho package/identifier/file Go, khiến `Shared/coding-style.md` không có đích cite cho phần
  naming theo stack Server. Migration: N/A — không có artifact phụ thuộc.
- **README.md — precedence exception, bảng nhóm, bullet CHANGELOG**: Rationale: mục Precedence
  chưa nêu ngoại lệ khi Shared explicitly delegate domain naming cho stack rules; bảng 3 nhóm
  còn liệt kê `performance` sau khi file bị xóa; mục Thêm rule mới chưa dẫn quy trình ghi
  CHANGELOG khi sửa rule hiện có. Migration: N/A — không có artifact phụ thuộc.
- **Xóa Shared/performance.md**: Rationale: file chứa hướng dẫn chọn model AI và quản lý
  context window (claim marketing dễ lỗi thời), không phải rule của project — model
  selection thuộc `CLAUDE.md` của host; tên file gây nhầm với runtime performance (SoT tại
  `Unity/module-constraints.md` §Hot-Path Allocation Budget). Migration: link duy nhất trỏ
  tới file này (bảng lens `cross-stack quality` trong `skills/ndv-audit-code/SKILL.md`) đã
  đổi sang `Shared coding-style/security`.
- **Unity/security.md, Unity/module-constraints.md — bỏ `paths:` frontmatter**: Rationale:
  frontmatter `paths:` giới hạn auto-load rule theo glob `**/*.cs`/`**/*.csx`, trong khi hai
  rule này áp dụng cả cho audit và review không edit trực tiếp file code. Migration: project
  đã adopt bản copy của hai file này vào `.claude/rules/` cần xóa cùng block `paths:` ở bản
  copy để giữ nhất quán với bản kit.
- **Shared/constitution.md — thêm ngoại lệ brownfield discovery**: Rationale: Context Loading
  Protocol cấm đọc code trước, nhưng bước DISCOVER của `/ndv-onboard` cho project chưa có
  register buộc đọc code như observed source duy nhất. Migration: N/A — không có artifact phụ
  thuộc.
- **Unity/ui-theming.md — bảng Audit criteria thêm reskinReady**: Rationale: bảng Audit
  criteria đo từng vi phạm token/inline-literal riêng lẻ nhưng chưa có metric tổng hợp cho
  biết một screen đã reskin-ready hay chưa. Migration: N/A — không có artifact phụ thuộc.
- **Unity/module-constraints.md — Module Shape thêm carve-out Editor/Test**: Rationale: closed
  list layer folder chưa khai báo `Editor/` và `Test/`, khiến hai subfolder non-runtime này bị
  tính là folder undeclared vi phạm. Migration: N/A — không có artifact phụ thuộc.
- **Shared/id-plan.md — sửa quantifier mơ hồ trong Range design rules**: Rationale: `~80%` là
  quantifier mơ hồ, vi phạm chính banned-phrase list của `ai-discipline.md` R5/R10. Migration:
  N/A — không có artifact phụ thuộc.
- **Unity/conventions.md — bảng Class Suffix thêm suffix View**: Rationale: bảng Class Suffix
  Conventions có `Controller` cho MVC nhưng thiếu suffix cho lớp presentation `View` cặp với
  nó. Migration: N/A — không có artifact phụ thuộc.
