---
name: ndv-lesson
description: "Lỗi agent lặp lại → thêm một check máy chạy được (deps.rules, test, hoặc script trong <ndvRoot>/checks/) để lỗi không quay lại; chỉ khi không kiểm được bằng máy mới thêm MỘT dòng rule đúng scope."
argument-hint: "[<mô tả lỗi lặp lại>]"
user-invocable: true
allowed-tools: Read, Glob, Grep, Bash, Write, Edit, AskUserQuestion
---

Config: `.claude/ndvkit/ndvkit.config.json` → `ndvRoot` (vắng → `.ndv`).

1. **Lỗi là gì.** Từ argument, hoặc từ lần `/ndv-verify` đỏ lặp lại trong session: pattern (vd
   `FindObjectOfType` trong `Update`, UI gọi thẳng Save, quên unsubscribe event), nơi xảy ra, vì sao nó
   lọt qua các check hiện có.
2. **Chọn check máy rẻ nhất bắt được nó**, theo thứ tự:
   1. Dependency sai hướng → thêm dòng `<folder> <namespace>` vào `<ndvRoot>/deps.rules` (dưới
      `# manual`).
   2. Hành vi sai → một EditMode test tái hiện lỗi (cần test asmdef; chưa có thì bỏ qua lựa chọn này).
   3. Pattern trong code → `<ndvRoot>/checks/<tên>.sh`: grep có giới hạn thư mục, in `file:line` mỗi
      hit, exit 1 khi có hit, exit 0 khi sạch. `/ndv-verify` chạy mọi file trong thư mục này.
   Grep trúng nhầm nhiều (false positive) → thu hẹp pattern hoặc thư mục, không bỏ check.
3. **Không kiểm được bằng máy** (vd quy ước đặt tên event có ngữ nghĩa) → MỘT dòng vào rule của host
   ở `.claude/rules/`, file có `paths:` khớp vùng code liên quan; chưa có file phù hợp → tạo file mới
   với `paths:` hẹp. Không sửa rule của kit (`.claude/ndvkit/rules/` là bản mặc định dùng chung).
4. **Chạy thử ngay** check vừa thêm trên code hiện tại. Bắt trúng chỗ cũ chưa sửa → báo danh sách,
   `AskUserQuestion`: sửa luôn trong task này / ghi nợ kỹ thuật vào progress (nếu có) và thu hẹp check
   / bỏ check.
5. Report: lỗi · check đã thêm (path + cách nó bắt) · kết quả chạy thử.

**Tiếp theo:** `/ndv-verify` — chắc check mới không báo nhầm và task hiện tại vẫn xanh.
