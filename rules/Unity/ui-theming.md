# UI Theming & Reskin — design token, screen skeleton, reuse

Chuẩn theming cho UI Toolkit: client phải reskin được như swap CSS theme trên web — đổi theme
= sửa MỘT token block, không sửa từng screen. Mọi appearance literal né token là vi phạm
per-line. `<uiRoot>` = folder UI chính của project (declare trong host rules; vd `Assets/UI`).

## Design token — single source

- Toàn estate có ĐÚNG MỘT `:root` token-definition block, ở MỘT file token source duy nhất
  (vd `<uiRoot>/Common/uss/Common.uss`). Mọi file `.uss` khác KHÔNG được chứa `:root` — kể
  cả `:root` rỗng hay `:root` khai nhóm token riêng. Token mới thêm vào token source này.
- Hai định nghĩa token trùng tên mang giá trị khác nhau (token collision) là functional bug —
  theme swap cho kết quả không xác định.
- Token set phủ đủ 8 axis: color · radius · spacing · font-size · font-family · border-width
  · opacity · duration. Axis chưa có token → mở rộng token source TRƯỚC rồi mới style —
  không lấy "chưa có token" làm lý do hardcode literal.
- Token đặt tên `--<scope>-<name>` (casing theo [naming-ui-toolkit.md](naming-ui-toolkit.md)).

## Appearance literal — cấm ngoài token block

- USS rule body KHÔNG chứa appearance literal: hex `#RRGGBB(AA)`, `rgb()`/`rgba()`, named
  color, `font-size: <n>px`. Mọi giá trị appearance resolve qua `var(--token)`. Literal chỉ
  hợp lệ BÊN TRONG `:root` token block.
- UXML inline `style="…"` mang color literal hoặc size literal (px) bị CẤM — inline literal
  invisible với theme swap. Appearance đi qua USS class kebab-case resolve về token.
- Layout thuần phần trăm/flex trong UXML (`width: 100%`, `flex-direction: row`) không phải
  appearance literal — được phép inline; giá trị px và mọi color thì không.
- CARVE-OUT — shader material arg: color/số bên trong `prop("…")` của `-unity-material` là
  property arg truyền vào shader (tương tự asset ref trong `url()`), KHÔNG phải USS style
  value — literal ở đây hợp lệ. Formula đếm literal loại trừ dòng match `-unity-material.*prop\(`.
- Tên USS class không mã hóa appearance ([naming-ui-toolkit.md](naming-ui-toolkit.md)).

## Screen skeleton

- Mỗi screen UXML có ĐÚNG MỘT root container được đặt tên `<screen>Root` (camelCase) wrap
  toàn bộ block của screen. Theme class / layout pattern per-screen hang vào root này —
  topBar hay content block KHÔNG được kiêm screen root.
- Element `name` phải UNIQUE trong một UXML tree khi code resolve bằng `Q("name")` PHẲNG từ
  root (first-match hazard). CARVE-OUT — tên trùng HỢP LỆ khi: (a) mỗi bản nằm dưới một
  parent có `name` unique và code scope `Q()` qua parent đó; HOẶC (b) code resolve đa-phần
  tử chủ đích bằng `Query<T>("name")` — multi-collect, trùng tên là ĐIỀU KIỆN CẦN. Duplicate
  còn lại (decorative không query, hoặc hand-inlined lặp không template) là finding §Reuse.
  `<ui:Template name="…">` là template alias — không tính vào phép đếm unique, nhưng alias
  phải đặt đúng tên component nguồn.
- Một screen chỉ có MỘT UXML tree — hai tree song song phục vụ cùng screen là vi phạm.

## Reuse — shared component

- Fragment dùng bởi ≥2 screen phải sống ở MỘT chỗ shared, không copy-paste per screen:
  - UXML chrome dùng chéo screen → shared UXML folder của project, instance qua
    `<ui:Template>`+`<ui:Instance>` hoặc `CloneTree()`.
  - Style block dùng chéo screen → đúng MỘT file, tên PascalCase theo chức năng, tại shared
    USS folder; cấm tên mơ hồ (`Shared.uss`, `Generic.uss`, `Common2.uss`) hoặc tên mã hóa màu.
  - Token source file là ngoại lệ duy nhất nằm ngoài shared USS folder.
  - Trước khi sửa shared USS/UXML: liệt kê direct consumer, transitive screen consumer, load
    order; sau sửa verify toàn bộ consumer — không chỉ screen đang mở.
- Full-screen layout lặp ở ≥2 feature phải extract shared template và parameterize phần khác
  biệt; mỗi instance vẫn mang screen-root name riêng.
- Item lặp trong một screen (row/card × N) instance từ MỘT template — không hand-copy inline.
- Trong template dùng chung, element chỉ khác role/text/behavior giữa các screen mang MỘT
  element `name` generic — mỗi controller tự set text/handler theo mode. KHÔNG fork element
  `name` per-mode trong template chung rồi ẩn cái thừa. Fork name chỉ hợp lệ khi cấu trúc
  thật sự khác.

## Element-name contract (C# ↔ UXML)

- Mọi `Q("name")` / `Query("name")` / `Bind("name")` trong controller phải khớp một element
  `name=` trong UXML tree mà screen load. Dead bind (query không match element nào) là
  functional bug. Ngoại lệ: pending re-wire ([known-pitfalls.md](known-pitfalls.md)) — NOTE
  observational, không require fix; genuine dead bind (không subscriber/caller) mới là finding.

## Audit criteria (re-runnable; exclude third-party + Unity-generated folders)

| Metric | Target | Formula |
|---|---|---|
| tokenSourceCount | 1 | `grep -rln ":root" --include=*.uss <uiRoot>` |
| tokenCollisionCount | 0 | mọi cặp define `--<name>:` trùng tên khác giá trị |
| hardcodedColorLiterals | 0 | `grep -rnE "#[0-9a-fA-F]{6,8}\|rgba?\(" --include=*.uss <uiRoot>` trừ dòng trong `:root` block và dòng match `-unity-material.*prop\(` |
| hardcodedSizeLiterals | 0 | `grep -rnE "font-size:\s*[0-9]+px" --include=*.uss <uiRoot>` |
| inlineStyleLiterals | 0 | `grep -rnE "style=\"[^\"]*(#[0-9a-fA-F]{6,8}\|rgba?\(\|[0-9]+px)" --include=*.uxml` |
| tokenAdoptionPct | ≥95% | số ref `var(--…)` ÷ (var refs + rule-body appearance literals) |
| tokenAxisCoveragePct | 100% | số axis có token ÷ 8 |
| screenSkeletonConformancePct | ≥95% | UXML có đúng một named `<screen>Root` ÷ tổng screen UXML |
| duplicateElementNameCount | 0 | per-UXML: `name=` value ≥2 lần (trừ Template alias) MÀ có `Q("name")` phẳng chứa >1 bản; loại dup scoped-per-unique-parent + `Query<>()` multi-collect + decorative-unqueried |
| reuseCoveragePct | ≥90% | shared component fragment ÷ (shared + copy-paste fragment) |
| inlineDuplication | 0 | UXML/USS block duplicated ≥2 chỗ |
| codeBuiltVisualElementCount | 0 | `grep -rnE "new (VisualElement\|Label\|Button\|Image\|ScrollView\|TextField\|Toggle)\(" --include=*.cs` trừ `Editor/**`, `Test/**` |
