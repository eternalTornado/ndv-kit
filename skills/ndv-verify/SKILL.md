---
name: ndv-verify
description: "Verify loop của ndvkit v2: compile + console qua Unity MCP, check-deps, các check của project, Unity tests, rồi đánh dấu từng acceptance criterion. Xanh hết mới ghi verified.stamp (Stop hook dựa vào stamp này). Chạy sau mọi lần sửa .cs."
argument-hint: "[--playmode] [--full]"
user-invocable: true
allowed-tools: Read, Glob, Grep, Bash, Write, Edit
---

Verify thay đổi hiện tại cho tới khi biết chắc xanh hay đỏ. Skill không sửa code: đỏ thì agent đang
làm task sửa rồi chạy lại.

## Config

`.claude/ndvkit/ndvkit.config.json` → `ndvRoot` (vắng → `.ndv`), `codeRoots`, `verifyNote`.
`verifyNote` là cách verify của project (MCP server, lệnh, fallback): làm đúng theo nó; mục dưới chỉ
là thứ tự và tiêu chí.

## Các bước (dừng ở bước đầu tiên đỏ chỉ khi bước sau phụ thuộc nó)

1. **Compile + console.** Theo `verifyNote` (Unity MCP: `read_console` clear → `refresh_unity`
   force compile, chờ xong → `read_console` lọc error/warning). Error → đỏ, dừng (test không chạy
   được trên code không compile). Warning: đỏ nếu `verifyNote` yêu cầu 0 warning, còn lại liệt kê.
   Không verify được (MCP không trả lời, Editor đóng, fallback cũng không đọc được) → **không xanh**:
   báo "chưa verify được" + lý do, không ghi stamp.
2. **Dependency.** `bash .claude/ndvkit/scripts/check-deps.sh`. Exit 1 → đỏ, kèm vi phạm.
3. **Check của project.** Mỗi `<ndvRoot>/checks/*.sh` (do `/ndv-lesson` thêm): `bash <file>`, exit ≠ 0
   → đỏ, kèm output.
4. **Test.** Project có test asmdef (Grep `"UnityEngine.TestRunner"` hoặc `"nunit.framework.dll"`
   trong `**/*.asmdef` dưới `Assets/`):
   - Luôn: `run_tests` mode `EditMode` toàn bộ (regression, rẻ) → `get_test_job` với `wait_timeout`
     30–60 cho tới khi xong.
   - `--playmode`, `--full`, hoặc brief/milestone đang làm yêu cầu: thêm `PlayMode`
     (`init_timeout` 120000).
   - Fail → đỏ, kèm tên test + message. Chưa có test asmdef → ghi "không có test", không đỏ.
5. **Criteria.** Có brief đang làm (brief của task M trong session, hoặc milestone hiện tại trong
   `<ndvRoot>/<feature>/progress.md`): mỗi acceptance criterion → `✅` (evidence: tên test xanh, dòng
   console, file:line) · `❌` (evidence) · `⚪` (không máy kiểm được — để reviewer và người kiểm).
   Criterion `❌` → đỏ. `--full` (integration task L): dùng criteria tổng của `brief.md`.
6. **Stamp.** Bước 1–5 không đỏ → `mkdir -p <ndvRoot> && touch <ndvRoot>/verified.stamp`. Đỏ → không
   ghi stamp.

## Report

Bảng ngắn: compile · deps · checks · tests (EditMode x/y, PlayMode x/y | không có) · criteria — mỗi
dòng ✅/❌ + evidence của cái đỏ. Không dán log dài.

**Tiếp theo** (một dòng, theo kết quả):
- Đỏ → không đề xuất lệnh: sửa lỗi rồi `/ndv-verify` lại (Stop hook sẽ chặn kết thúc).
- Đỏ, cùng lỗi (cùng message hoặc cùng test) đã đỏ ở lần verify trước trong session → `/ndv-lesson`.
- Chưa verify được → mở Unity Editor / bật MCP rồi `/ndv-verify`.
- Xanh, task S (không có brief) → xem diff rồi commit.
- Xanh, task M hoặc milestone → spawn `ndv-reviewer` (bước review của `/ndv-brief`).
- Xanh với `--full` → người playtest theo criteria `⚪`, rồi đóng feature.
