# Rules changelog

File này là nơi DUY NHẤT ghi amendment cho rules của kit (written rationale + migration note
theo [Shared/constitution.md](Shared/constitution.md) §Governance). Body của rule file chỉ
chứa current state (R9.1).

## 2026-10-10 — Bỏ tầng TDD: wording Shared/ai-discipline.md, Server/server.md + migrate host

- **Rationale**: kit bỏ tầng TDD (Technical Design Document) theo quyết định của user — GDD sang
  thẳng `requirement.md` + `specify.md` qua `/ndv-gdd-to-spec` (một workflow multi-agent, hỏi user
  giữa các stage); `/ndv-gdd-to-tdd`, `/ndv-tdd-to-spec`, agent `tdd-writer`, template
  `tdd-template.md` và key `tddRoot` bị xóa. Ví dụ "TDD" trong R1/R3/R4 của
  `Shared/ai-discipline.md` và cụm "spec/TDD" ở đoạn mở đầu `Server/server.md` trỏ vào artifact
  không còn tồn tại — đổi sang GDD / requirement / specify / spec; nghĩa rule và đánh số R không đổi.
  "TDD" trong `Shared/constitution.md` §Testing policy là test-driven development — giữ nguyên.
- **Migration**: cite vào `ai-discipline.md` / `server.md` giữ nguyên anchor — không cần cite-only
  edit. Host có artifact từ pipeline cũ (`/ndv-sync`, `/ndv-onboard status` báo `legacy-tdd`):
  - requirement.md còn cite TDD (`tdd-source`, Source trỏ `<tddRoot>/…`) → chạy
    `/ndv-gdd-to-spec <Feature> --update`: stage author re-cite sang GDD anchor mà TDD đó quote
    (spec-writer §Mode forward); câu TDD mang `decision:` → giữ decision (kèm GDD anchor của
    section; GDD nay có literal cho điểm đó → cite GDD), không hỏi lại; không có GDD cite lẫn
    decision → `NEEDS CLARIFICATION`; không còn row nào cite TDD → xóa `tdd-source`; specify.md
    được compose lại ở stage specify khi module hết marker. Mọi module của feature đã re-cite → user
    tự archive `<tddRoot>/<Feature>/` (kit không xóa).
  - requirement.md `origin: reverse-engineered` còn cite TDD (as-built cũ, TDD `gdd-sources: N/A`
    nên `--update` không chạm) → `/ndv-onboard reverse-doc <MODULE>`: spec-writer §Mode as-built
    re-cite về code symbol, xóa `tdd-source`; xong mới archive TDD tương ứng.
  - `ndvkit.config.json`: xóa key `tddRoot` (`ndv_check.py` bỏ qua nếu còn).
  - `modules.json`: field `tdd` bị script bỏ qua; `plannedDepEvidence` trỏ `<tddRoot>` không còn
    được check → trước khi archive TDD chạy `/ndv-module-matrix` (không arg, Mode full): xóa `tdd`,
    re-cite/bỏ planned edge có evidence TDD theo Contract surface rows.
  - Activation: xóa link/copy cũ `.claude/skills/ndv-gdd-to-tdd`, `.claude/skills/ndv-tdd-to-spec`,
    `.claude/agents/tdd-writer.md`, re-copy `agents/*.md` (README §Activation).

## 2026-09-20 — Unity/ui-theming.md: formula Audit criteria chạy được + deadBindCount

- **Rationale**: formula trong bảng §Audit criteria viết alternation dạng `\|` (escape của
  markdown table) — copy nguyên văn vào `grep -E` trả 0 hit trên macOS, nên mọi metric target 0
  (`hardcodedColorLiterals`, `inlineStyleLiterals`, `codeBuiltVisualElementCount`) luôn đạt giả;
  đồng thời protocol audit cấm `\|`. `--include=*.uss` không nháy vỡ trên zsh. Procedure
  anti-miss dead-bind chỉ sống trong agent audit, không nằm trong bộ chuẩn.
- **Migration**: formula chuyển xuống code block F-01…F-05 (`|` thường, `--include` trong nháy
  đơn); thêm metric `deadBindCount`. Report audit cũ có metric target 0 đo bằng formula cũ cần
  chạy lại — giá trị 0 trong đó không đáng tin.

## 2026-09-20 — Shared/ai-discipline.md: tách worker core / session, thêm cite `decision:`

- **Rationale**: mọi sub-agent đọc cả 11KB R1–R10 mỗi lần spawn trong khi worker chỉ cần
  R1–R5 + R7; R6, R8–R10 + governance chỉ áp cho main session. Banned quantifier lặp ở R5 và
  R10. Câu trả lời của user khi resolve `NEEDS CLARIFICATION` không có form cite hợp lệ theo R3.
  R1/R7/Enforcement còn nêu tên ba audit skill sau khi kit gộp về một `/ndv-audit-code`.
- **Migration**: R6, R8, R9, R9.1, R10, Exception, Enforcement, Governance chuyển sang
  `Shared/ai-discipline-session.md` (số R giữ nguyên). Cite dạng
  `ai-discipline.md#r6…|#r8…|#r9…|#r10…` trong artifact host → đổi sang
  `ai-discipline-session.md#…` như một cite-only edit (`/ndv-sync` báo `broken-cite`). Quantifier
  list: SoT ở R5, R10 cite-back. R3 thêm form `decision: <yyyy-mm-dd> — "<answer>"`; R9.1 cho
  phép form này trong body. `Shared/constitution.md` §Context Loading Protocol: ngoại lệ
  brownfield đổi tên bước theo `/ndv-onboard` mới (không còn agent `onboarder`).

## 2026-09-19 — R1: cite rule file bằng path đã mở

- **Rationale**: một lượt chạy pipeline trên host không adopt rules sinh 150 cite dạng
  `<rulesRoot>/Unity|Shared/<file>.md` trong 19 file trỏ vào file không tồn tại (file thật nằm
  dưới `<kitRulesRoot>`); nguyên nhân: tên ngắn `Unity/…` trong rules bị ghép với `<rulesRoot>`,
  và không bước nào của pipeline verify cite vào doc/rule.
- **Migration**: host thay `<rulesRoot>/(Unity|Shared|Server)/` → `<kitRulesRoot>/\1/` ở những
  cite mà file không tồn tại dưới `<rulesRoot>`, thực hiện như một cite-only edit (`/ndv-sync`
  §Cite-only edit); `/ndv-sync` Phase 1 báo các cite này là `broken-cite`.

## 2026-09-19 — Bulk re-anchor thay lazy migration cho cite code

- **Rationale**: lazy migration (entry 2026-09-18 bên dưới) khiến anchor vỡ trước rồi mới được
  chuyển: một lượt implement thêm 30 dòng vào một file làm vỡ thêm 6 anchor ở artifact của
  module khác.
- **Migration**: chạy `/ndv-sync --reanchor` một lần cho cả estate (script
  `skills/ndv-sync/scripts/ndv_check.py`); anchor không còn khớp giữ nguyên và được báo
  `broken-cite`; thay cho ghi chú "không migrate hàng loạt" của entry 2026-09-18.
  `/ndv-implement` Phase 3 chạy cite sweep sau mỗi lượt implement.

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
