---
name: ndv-brief
description: "Task M hoặc L của ndvkit v2. M: Explore code → brief một trang (acceptance criteria kiểm được) → user duyệt → implement cùng session → /ndv-verify → ndv-reviewer. L: --L viết L-brief + milestones; '<feature> M<n>' chạy một milestone trong session mới; --replan sửa L-brief."
argument-hint: "<mô tả task> | <feature> --L | <feature> M<n> | <feature> --replan [<lý do>]"
user-invocable: true
allowed-tools: Read, Glob, Grep, Bash, Write, Edit, Task, AskUserQuestion, TodoWrite
---

Chỉ main session nói chuyện với user. Config: `.claude/ndvkit/ndvkit.config.json` → `gddRoot`,
`ndvRoot` (vắng → `.ndv`), `codeRoots`. Rule source: host `.claude/rules/**` + `CLAUDE.md` thắng, kit
`.claude/ndvkit/rules/**` cho domain host không define. Template: `.claude/ndvkit/templates/`.
`base` = `git rev-parse HEAD` lúc bắt đầu task (reviewer diff từ đây).

Task 1–2 file, yêu cầu rõ → không cần skill này: làm thẳng, Stop hook ép `/ndv-verify`.

## Mode M — `<mô tả task>`

1. **Explore.** Spawn subagent `Explore` (medium): tìm module trong `<ndvRoot>/blueprint.json` liên
   quan, file và symbol sẽ chạm, test hiện có của vùng đó. Nhận về bản đồ ngắn, không đọc cả repo vào
   main context. Task đến từ `/ndv-impact` (`I-<n>`): đọc dòng đó trong file impact và đoạn GDD.
2. **Brief.** Theo `brief-template.md`, hiện trong chat:
   - Criteria 3–7 dòng, mỗi dòng kiểm được, cột "Kiểm bằng" ghi test cụ thể khi viết được test.
   - "Test thay đổi": mọi test hiện có sẽ phải sửa/xóa và vì sao. Reviewer flag test đổi ngoài danh
     sách này.
   - Chạm ranh giới module (module mới, dep mới) → ghi rõ; cập nhật `blueprint.json` là một phần của
     task (qua `/ndv-blueprint --update` trước khi code).
   - Không tự đoán điều chưa rõ: đưa vào "Câu hỏi mở".
3. **Duyệt.** Một `AskUserQuestion`: câu hỏi mở (nếu có, ≤3) + "Duyệt brief?" — Approve / sửa (Other).
   Sửa → cập nhật brief, hỏi lại.
4. **Implement** ngay trong session này, đúng "Sẽ sửa"; cần sửa thêm file → nói lý do khi report.
   Test cho criterion có "Kiểm bằng" là test: viết cùng lúc với code.
5. **Verify.** `/ndv-verify` cho tới khi xanh (Stop hook chặn kết thúc khi chưa xanh).
6. **Review.** Spawn `ndv-reviewer` (Task; agent type `ndv-reviewer`) với: criteria, "Sẽ sửa",
   "Test thay đổi", đoạn GDD (nếu có), `base`, bảng kết quả `/ndv-verify`, path blueprint/deps.rules.
   Finding `blocker`/`critical`/`high` → sửa → `/ndv-verify` → review lại một lần. Còn lại → báo user.
7. **Report:** `git diff --stat <base>` · bảng criteria ✅/❌/⚪ · finding còn lại · file ngoài "Sẽ sửa".
   Task từ `/ndv-impact`: đổi trạng thái dòng `I-<n>` thành `done` (chưa commit thì ghi `done`, commit
   sau). Không commit.

**Tiếp theo:** người đọc report rồi commit · còn finding `medium` muốn sửa → nói sửa gì · task từ
impact → `/ndv-impact` (dòng kế tiếp hoặc đóng vòng).

## Mode L — `<feature> --L`

1. Slug `feature` = kebab-case ASCII. `<ndvRoot>/<feature>/brief.md` đã có → hỏi: Replan hay tên khác.
2. Explore (thorough): module liên quan trong blueprint, code hiện có, đoạn GDD của feature.
3. Viết `<ndvRoot>/<feature>/brief.md` theo `l-brief-template.md` (`Approved: pending`) và
   `progress.md` theo `progress-template.md` (Current = milestone đầu). Milestone: rủi ro cao trước;
   mỗi cái vừa một session và kết thúc ở compile được + test xanh + commit được; điểm mù kỹ thuật
   lớn → M0 spike.
4. **Duyệt** (chỗ đáng đầu tư thời gian người nhất): tóm tắt Goal, Decisions, bảng Milestones trong chat;
   `AskUserQuestion` Approve / sửa (Other). Approve → `Approved: <date>`.

**Tiếp theo:** session mới → `/ndv-brief <feature> M1` (hoặc `M0` nếu có spike).

## Mode milestone — `<feature> M<n>`

1. Đọc `brief.md` (chỉ Goal, Decisions, dòng `M<n>`, Out of scope) và `progress.md`. Không đọc lịch
   sử session trước. `Approved: pending` → dừng, yêu cầu duyệt L-brief trước.
2. Explore như mode M, giới hạn ở module của `M<n>`.
3. **Mini-brief** theo `brief-template.md`, criteria lấy từ dòng `M<n>` và tinh chỉnh theo code thực
   tế. Lệch Decisions hoặc thứ tự milestone không còn hợp lý → **Replan** (mode dưới), dừng.
4. Duyệt nhanh (`AskUserQuestion` Approve / sửa), rồi bước 4–6 của mode M. Verify chạy toàn bộ
   EditMode test để bắt regression của milestone trước.
5. Cập nhật `progress.md`: thêm `M<n> ✅` vào Done, Current = milestone kế, Known issues, Lệch so với
   brief. `AskUserQuestion`: "Commit milestone?" — Commit (`git commit -m "<feature> M<n>: <goal>"`
   chỉ các file của task + progress.md) / Tôi tự commit.
6. Milestone cuối: `/ndv-verify --full` (EditMode + PlayMode, criteria tổng A1…), rồi liệt kê criteria
   `⚪` cho người playtest.

**Tiếp theo:** còn milestone → session mới `/ndv-brief <feature> M<n+1>` · milestone cuối → người
playtest theo danh sách, rồi feature xong.

## Mode Replan — `<feature> --replan [<lý do>]`

Đề xuất sửa `brief.md` (Decisions, milestone, criteria tổng) với lý do và milestone bị ảnh hưởng; ghi
vào "Lệch so với brief" của `progress.md`. `AskUserQuestion` Approve / sửa. Approve → ghi brief,
`Approved: <date>`. Agent không bao giờ tự đổi hướng mà không qua bước này.

**Tiếp theo:** `/ndv-brief <feature> M<current>` trong session mới.
