# Quy tắc đặt tên trong Unity UI Toolkit

| Thành phần UI | Định dạng (Casing) | Ví dụ | Quy ước / Quy chuẩn | Mục đích & Lưu ý |
|---|---|---|---|---|
| **File Cấu trúc UI** | PascalCase | `MainMenuWindow.uxml` | Đặt tên theo tên màn hình/tính năng. | File chứa bố cục giao diện. |
| **File Định dạng UI** | PascalCase | `MainMenuWindow.uss` | Trùng tên với file UXML tương ứng. | File chứa thuộc tính thiết kế. |
| **File Code Logic** | PascalCase | `MainMenuController.cs` | Hậu tố `Controller` — screen theo MVC: class `Controller` (behavior) + class `View` (presentation); KHÔNG dùng `Presenter` / `ViewModel` cho screen. | File C# xử lý sự kiện và dữ liệu UI. |
| **Element Name (ID)** | camelCase | `healthBarImage` | Thêm hậu tố loại linh kiện (`Btn`, `Lbl`, `Img`). | Thuộc tính `name` trong UI Builder. Unique trong tree khi query `Q("name")` phẳng (first-match). Tên trùng HỢP LỆ khi query scoped qua parent unique hoặc multi-collect `Query<T>("name")`. |
| **Screen Root** | camelCase + hậu tố `Root` | `heroListRoot`, `shopRoot` | `<screen>Root` — đúng MỘT root container được đặt tên per screen UXML, wrap toàn bộ block. | Wrapper duy nhất để hang theme/layout class per-screen; topBar/content không kiêm root ([ui-theming.md](ui-theming.md)). |
| **Template alias** | PascalCase, trùng tên component nguồn | `<ui:Template name="TopBar" src=".../TopBar.uxml">` | Alias = tên component được instance; cấm alias lệch/typo. | `<ui:Template name>` là alias đăng ký template, KHÔNG phải element name — không tính vào phép đếm unique. |
| **USS Class (Chung)** | kebab-case | `.panel-background` | Viết thường, phân tách `-`. | Tái sử dụng style cho nhiều phần tử. |
| **Biến C# (UI Element)** | camelCase | `Button startBtn;` | Trùng/tương tự Element Name trong UXML. | Tham chiếu element trong code. |
| **Hàm xử lý sự kiện** | PascalCase | `OnStartButtonClick()` | `On` + `[Tên Phần Tử]` + `[Hành Động]`. | Callback đăng ký với `ClickEvent`, `ChangeEvent`. |

> Element name generic/type-only thiếu descriptor (`frame`, `portrait`, `mask`, `image`,
> `fill`) — đặt lại tên ngữ nghĩa DERIVE từ **parent-chain** (parent → grandparent → … tới
> khi đủ ngữ nghĩa) HOẶC từ **controller đang query** nó: `frame` con của portrait →
> `portraitFrame`; `image` con của healthBar → `healthBarFrame`. RÀNG BUỘC — element được
> query SCOPED-UNIFORM qua nhiều bản lặp (một code path `parent.Q("child")` chạy cho mọi
> bản) PHẢI giữ tên ĐỒNG NHẤT: derive từ ancestor loại-đơn-vị-lặp (`slot`/`card`/`row`),
> KHÔNG từ instance cụ thể — đặt khác nhau per-instance sẽ phá scoped query. Rename derive
> luôn wire sang mọi `Q()`/`Query()`/`Bind()` C# trong cùng change.

> USS class: kebab-case thuần — không dùng BEM `__` / `--`; USS class chỉ để style/skin.

> USS class name KHÔNG mã hóa appearance vào tên (`.blue-box`, `.big-text`) — đặt tên theo
> ngữ nghĩa/state (`.hp-bar-fill-high` / `-mid` / `-low`). Reskin đổi màu thì tên class mã
> hóa màu thành lời nói dối; đổi tên class phải update đồng bộ `.uxml` + `.uss` + mọi
> `AddToClassList`/`EnableInClassList` C# trong cùng một change.
