# ndvkit — GDD → Module Blueprint → Spec (EARS) + ModuleMatrix → Plan → Implement pipeline

Bộ agents + skills PORTABLE cho vòng đời feature game project, format theo
[Claude-Code-Game-Studios](https://github.com/Donchitos/Claude-Code-Game-Studios) `.claude/`.
Kit không chứa reference cứng vào một project cụ thể — mọi giá trị per-project nằm ở
`ndvkit.config.json`, mọi convention per-project defer về `.claude/rules/**` của project host.

## ndvkit v2 — Tổng quan

> **Trạng thái:** thiết kế v2 đã được duyệt và chốt các quyết định mở (2026-11-06), chưa triển khai. Các mục từ
> [Cài đặt](#cài-đặt) trở xuống vẫn mô tả **v1 đang chạy** cho tới khi chuyển đổi xong.

ndvkit v2 là bộ cấu hình harness cho Claude Code trên dự án Unity. Mục tiêu: nhanh và đúng ý
hơn việc giao task thẳng cho agent, với ít token hơn v1.

### Vì sao cần v2

v1 tốn nhiều token hơn giao task thẳng, mà kết quả lại kém hơn: implement lâu, sai ý, audit mất
thời gian. Bốn nguyên nhân gốc:

- **Mất context giữa các bước.** Chuỗi requirement → specify → plan → tasks → implement bắt mỗi
  bước đọc lại artifact của bước trước. Agent phải hiểu lại code qua tài liệu, vừa tốn token vừa
  lệch dần.
- **Intent bị pha loãng.** Spec do agent viết dài, người không đọc kỹ được. Sai ý từ đầu lọt qua
  rồi bị khuếch đại ở các bước sau.
- **Rules nạp quá nhiều.** Mọi agent đọc toàn bộ host rules + kit rules trước khi viết, kể cả khi
  task chỉ chạm một file.
- **Audit đắt.** Người phải đọc spec, report và code để đối chiếu, trong khi máy làm phần lớn
  việc này nhanh và rẻ hơn.

v2 giữ ưu điểm của giao task thẳng (context liền mạch, intent nguyên gốc) và chỉ thêm hai thứ:
**chốt intent rẻ** và **verify bằng máy**.

### Nguyên tắc thiết kế

Token nên tiêu vào kiểm chứng kết quả, không tiêu vào viết tài liệu.

1. **Ít artifact, nhiều verification.** Chỉ giữ tài liệu mà agent hoặc người thực sự đọc lại.
2. **Intent chốt bằng acceptance criteria kiểm được.** Người duyệt criteria trong khoảng 1 phút,
   không duyệt spec dài.
3. **Workflow theo độ lớn task.** Không task nào phải đi qua đủ mọi bước.
4. **Giữ context liền mạch.** Brief và implement chạy cùng session; chỉ tách session ở ranh giới
   milestone.
5. **Ép bằng máy trước, nhắc bằng chữ sau.** Rule nào kiểm được bằng code thì chuyển thành hook,
   script hoặc test.
6. **Audit bằng máy trước, người sau.** Người chỉ đọc diff stat, bảng criteria và findings.
7. **Mỗi lỗi lặp lại thành một check mới.** Harness mạnh dần lên, còn rules không phình ra.
8. **Skill nào xong cũng đề xuất bước tiếp theo.** Người không phải nhớ flow; xem
   [Quy ước bước tiếp theo](#quy-ước-bước-tiếp-theo).

### Tầng tài liệu: GDD → Blueprint → Brief

v2 bỏ TDD như một bước bắt buộc. Blueprint là tầng duy nhất cấp project, ngắn và sống cùng code.

| Tầng | Ai viết | Phạm vi | Agent đọc khi nào |
| --- | --- | --- | --- |
| GDD | Người | Design intent của game | Chỉ phần liên quan, được trích vào brief |
| Blueprint | Agent đề xuất, người duyệt | Cả project: `.ndv/blueprint.json` (data) + `blueprint.html` (view do script sinh) | Mỗi lần viết L-brief hoặc brief chạm ranh giới module |
| Brief | Agent viết, người duyệt criteria | Một task hoặc một feature | Suốt task |

Blueprint giữ nguyên format v1: `blueprint.json` là data SoT, `ndv_blueprint.py` lo `--check`
(schema, id, cycle, Foundation không depend `game`, cite GDD + code), `--render` (sinh
`blueprint.html` từ `templates/blueprint-template.html`), `--approve` và `--code-graph`. Schema
nằm ở `module-architect` (§Mode blueprint). Nội dung: band Foundation, Layer 1..n, core loop band,
deps consumer → owner kèm contract, decisions, out of scope.

Với project đã có code, `--code-graph` đưa SCC của code hiện có cho architect để reverse-engineer
blueprint, rồi người duyệt. Milestone nào đổi ranh giới module thì cập nhật `blueprint.json` và chạy
`ndv_blueprint.py --check` trong cùng commit; reviewer flag nếu thiếu. `deps.rules` sinh từ deps
trong blueprint.

**TDD theo vùng rủi ro** chỉ viết khi cần: netcode multiplayer, save schema và migration,
performance budget mobile, hoặc khách freelance yêu cầu tài liệu nghiệm thu.

### Phân tier S/M/L

| Tier | Khi nào | Workflow | Người can thiệp |
| --- | --- | --- | --- |
| S | 1–2 file, yêu cầu rõ | Prompt thẳng, hooks lo verify | Đọc audit |
| M | Feature nhỏ, nhiều file | `/ndv-brief` → duyệt → implement cùng session → verify → review | Duyệt criteria khoảng 1 phút + đọc audit |
| L | Hệ thống mới, nhiều ngày | L-brief → các milestone, mỗi cái chạy như một task M → integration | Duyệt L-brief 10–15 phút, mỗi milestone 3–5 phút, playtest cuối |

### Flow task S và M

**Task S:** prompt thẳng như bình thường. Stop hook ép chạy `/ndv-verify` trước khi agent được báo xong.

**Task M:**

1. `/ndv-brief`: Explore subagent đọc code liên quan, giữ main context gọn.
2. Agent viết brief tối đa khoảng một trang:
    - **Goal:** 1–2 câu.
    - **Acceptance criteria:** 3–7 dòng, mỗi dòng kiểm được. Ví dụ: "Bấm Retry khi hết mạng thì
      gọi lại API tối đa 3 lần, test `RetryPolicyTests` pass".
    - **Sẽ sửa:** danh sách file.
    - **Out of scope.**
    - **Câu hỏi mở:** agent hỏi ở đây, không tự đoán.
3. Người duyệt acceptance criteria. Đây là điểm chặn sai ý rẻ nhất.
4. Implement ngay trong cùng session.
5. `/ndv-verify` cho đến khi xanh.
6. Reviewer subagent đối chiếu diff với criteria.
7. Người đọc audit rồi commit.

### Flow task L

Task L được cắt thành nhiều milestone (lát cắt dọc), mỗi milestone chạy như một task M trong một
session mới.

```text
L-brief ──► Người duyệt ──► Milestone N (session mới) ──► Còn milestone? ──hết──► Integration
            (10–15 phút)    đọc Decisions + progress.md        │                  full test + playtest
                 ▲          mini-brief → build → verify        │
                 │          reviewer → commit → progress.md    │
                 │               │            ▲                │
                 │           brief sai        └───── còn ──────┘
                 │               ▼
                 └───────── Replan (agent dừng, sửa brief)
```

**L-brief** (1–2 trang, ổn định suốt dự án):

- Goal + acceptance criteria tổng, kiểm được.
- Decisions: quyết định kiến trúc và lý do, sống qua nhiều session.
- Milestones: mỗi cái một dòng goal + 2–4 criteria, rủi ro cao làm trước.
- Out of scope.

Có điểm mù kỹ thuật lớn thì thêm milestone 0 là spike: prototype vứt đi, chỉ để trả lời câu hỏi
rồi cập nhật Decisions.

**Quy tắc cắt milestone:** vừa một session, kết thúc ở trạng thái compile được, test xanh, commit
được. Ví dụ Inventory + Save/Load + UI:

| # | Milestone | Verify |
| --- | --- | --- |
| M1 | Data model + add/remove/stack (pure C#) | EditMode tests |
| M2 | Save/Load inventory ra JSON | Test round-trip; file hỏng thì không crash |
| M3 | UI hiển thị + kéo thả | PlayMode test cơ bản + người nhìn |
| M4 | Nối gameplay: nhặt đồ, dùng đồ | PlayMode test + playtest |

**Mỗi milestone** chỉ nạp Decisions + milestone hiện tại, `progress.md`, và code liên quan qua
Explore subagent. Mini-brief khớp brief thì người liếc khoảng 30 giây. Mỗi milestone là một commit
làm checkpoint.

**`progress.md`** là bộ nhớ giữa các session, giữ ngắn:

```markdown
## Done
- M1 ✅ (a1b2c3) — InventoryModel, stacking theo maxStack
- M2 ✅ (d4e5f6) — SaveService; file hỏng → inventory rỗng + log warning
## Current: M3
## Known issues / nợ kỹ thuật
- Chưa xử lý migrate khi đổi schema save (để sau M4)
## Lệch so với brief
- (trống)
```

**Replan:** khi phát hiện Decisions sai hoặc thứ tự milestone không hợp lý, agent dừng, đề xuất sửa
brief và chờ người duyệt.

**Integration:** chạy full test suite, đối chiếu criteria tổng, rồi người playtest. Game feel và UX
không verify được bằng máy.

Milestone độc lập có thể chạy song song bằng git worktree, nhưng chỉ nên làm sau vài dự án tuần
tự, khi verify đã chắc.

### Verify loop và hooks

Agent không thể báo xong khi code chưa compile sạch và test chưa xanh. Đây là phần thực sự là
harness của v2.

`/ndv-verify` chạy qua Unity MCP:

1. Compile check theo `verifyNote` trong `ndvkit.config.json` (`refresh_unity`, rồi `read_console`
   lọc errors).
2. `check-deps.sh` kiểm dependency direction (xem phần Rules).
3. `run_tests` (Unity Test Framework, xem dưới) cho test assembly bị chạm, kèm toàn bộ EditMode
   tests để bắt regression. Project chưa có test thì bước này bỏ qua và báo rõ.
4. Đánh dấu ✅/❌ từng acceptance criteria.
5. Ghi stamp `.ndv/verified.stamp`.

**Stop hook** chặn agent kết thúc khi còn file `.cs` sửa sau stamp:

```json
// <project>/.claude/settings.json
{ "hooks": { "Stop": [ { "hooks": [
  { "type": "command", "command": "bash .claude/ndvkit/hooks/require-verify.sh" }
] } ] } }
```

```bash
#!/usr/bin/env bash
# hooks/require-verify.sh
input=$(cat)
echo "$input" | grep -q '"stop_hook_active": *true' && exit 0   # tránh loop vô hạn
changed=$( { git diff --name-only HEAD -- '*.cs'; git ls-files -o --exclude-standard -- '*.cs'; } )
[ -z "$changed" ] && exit 0
stamp=.ndv/verified.stamp
if [ ! -f "$stamp" ] || [ -n "$(find $changed -newer "$stamp" 2>/dev/null)" ]; then
  echo "Có .cs thay đổi chưa verify. Chạy /ndv-verify (compile + test) rồi mới kết thúc." >&2
  exit 2
fi
```

Exit code 2 chặn agent dừng và đưa thông báo ngược lại cho agent, nên nó tự sửa đến khi xanh.

**Test runner** là Unity Test Framework (package `com.unity.test-framework`, NUnit), chạy qua Unity
MCP: `run_tests` (lọc theo `mode`, `assembly_names`, `test_names`) rồi `get_test_job` lấy kết quả.

| Loại | Chạy ở đâu | Tốc độ | Dùng cho | Khi nào verify chạy |
| --- | --- | --- | --- | --- |
| EditMode | Trong Editor, không vào Play | Mili-giây tới vài giây | Logic thuần C#: công thức damage, stacking inventory, state machine, save/load round-trip, validate config | Mọi lần verify |
| PlayMode | Vào Play mode: có `Update`, coroutine, physics, scene | Chậm hơn (domain reload, `init_timeout` nên khoảng 120000 ms) | Spawn, scene flow, UI flow cơ bản | Khi brief ghi rõ, và ở integration tier L |

- Criteria nào kiểm được bằng test thì brief ghi tên test; agent viết test cùng lúc với code.
- Criteria về game feel hoặc UX không test: reviewer và người kiểm.
- Test nằm trong test asmdef (reference `UnityEngine.TestRunner`, `UnityEditor.TestRunner`,
  `nunit.framework.dll`). Asmdef không reference được `Assembly-CSharp`, nên module có logic cần test
  phải có asmdef riêng: test runner và mức 3 của ép dependency đi cùng nhau.
- Chỉ viết test cho logic dễ test trước; không đặt mục tiêu coverage.

### Audit: reviewer subagent

Người audit trong 2–3 phút, vì máy đã đối chiếu trước.

Reviewer subagent có context sạch và không thấy quá trình làm, nên không "chấm bài của chính
mình". Nó chỉ nhận acceptance criteria, `git diff` và `blueprint.json` (để bắt pattern lạ hoặc
module mới chưa khai báo). Nó trả về tối đa 5 điểm lệch, mỗi điểm có severity, kèm cờ nếu ranh giới module
đổi mà blueprint chưa cập nhật.

Người chỉ đọc ba thứ: diff stat, bảng criteria ✅/❌ từ `/ndv-verify`, và findings của reviewer.

### Rules và ép dependency

Rules ít, nạp theo scope, và ưu tiên ép bằng máy.

- `CLAUDE.md` dưới 100 dòng: project map, lệnh build/test, vài nguyên tắc không được vi phạm.
- Rules chi tiết nằm trong `.claude/rules/*.md` có `paths:` frontmatter (ví dụ
  `Assets/Scripts/Network/**`), chỉ nạp khi chạm file liên quan.
- Rule kiểm được bằng code (naming, cấm `Find*` trong `Update`, dependency) chuyển thành script,
  test hoặc analyzer.

Namespace một mình không chặn được gì: không có asmdef thì mọi script compile chung vào
`Assembly-CSharp`, mọi type `public` gọi được từ mọi nơi. v2 ép dependency theo ba mức:

| Mức | Cách | Độ chính xác | Chi phí |
| --- | --- | --- | --- |
| 1 | Namespace + `check-deps.sh` (grep theo `.ndv/deps.rules`) | Bắt phần lớn; lọt khi dùng alias hoặc `using` cha | Khoảng 15 phút, chạy dưới 1 giây |
| 2 | Architecture test bằng Mono.Cecil, hoặc Roslyn analyzer severity Error | Resolve type thật, cả trong thân hàm | Vài giờ |
| 3 | asmdef dần dần, bắt đầu từ `Core` | Compile fail khi vi phạm; thêm compile incremental | Tùy độ rối của project |

Khởi đầu: mức 1 ngay, tách asmdef cho `Core` khi có dịp. Asmdef không thể reference
`Assembly-CSharp`, nên `Core` tự động không phụ thuộc được gameplay hay UI.

```text
# .ndv/deps.rules — <thư mục> <namespace bị cấm>
Assets/Scripts/Core   Game.Gameplay
Assets/Scripts/Core   Game.UI
Assets/Scripts/UI     Game.Save
```

```bash
#!/usr/bin/env bash
# scripts/check-deps.sh
fail=0
while read -r dir ns; do
  [[ -z "$dir" || "$dir" == \#* ]] && continue
  hits=$(grep -rnF "$ns" "$dir" --include='*.cs')
  [ -n "$hits" ] && { echo "✗ $dir không được dùng $ns:"; echo "$hits"; fail=1; }
done < .ndv/deps.rules
exit $fail
```

### Vòng học từ lỗi: `/ndv-lesson`

Mỗi lỗi agent lặp lại lần thứ hai được biến thành một check, để nó không xảy ra lần thứ ba. Khi gọi
`/ndv-lesson`, agent chọn theo thứ tự ưu tiên:

1. Thêm một check máy chạy được: dòng mới trong `deps.rules`, một test, hoặc một hook.
2. Nếu không kiểm được bằng máy, thêm **một dòng** vào rules file đúng scope.

Khi một vi phạm lọt qua check hiện có (ví dụ grep bỏ sót), đó là tín hiệu nâng mức ép dependency.

### Cấu trúc v2

```text
.claude/ndvkit/                        # kit (repo này)
├── ndvkit.config.json                 # ndvRoot: ".ndv" thay cho matrixRoot / specsRoot / auditReportRoot
├── skills/
│   ├── ndv-blueprint/                 # giữ từ v1
│   │   └── scripts/
│   │       ├── ndv_blueprint.py       # --code-graph · --check · --render · --approve
│   │       └── ndv_check.py           # chỉ giữ phần ndv_blueprint.py dùng (config, cite, CodeIndex)
│   ├── ndv-brief/                     # brief task M; chế độ L cho L-brief + milestones
│   ├── ndv-verify/                    # compile, deps, test, bảng criteria, stamp
│   └── ndv-lesson/                    # lỗi lặp lại → check mới hoặc một dòng rule
├── agents/
│   ├── module-architect.md            # chỉ còn Mode blueprint + Mode blueprint-review
│   └── ndv-reviewer.md                # tối đa 5 điểm lệch có severity
├── hooks/require-verify.sh
├── scripts/check-deps.sh
├── rules/                             # tách dần thành check + rules có scope
└── templates/
    ├── blueprint-template.html        # giữ từ v1
    ├── brief-template.md
    ├── l-brief-template.md
    └── progress-template.md

<project>/
├── CLAUDE.md                          # < 100 dòng
├── .claude/settings.json              # Stop hook
├── .claude/rules/*.md                 # rules có paths: frontmatter
└── .ndv/                              # mọi artifact của kit
    ├── blueprint.json
    ├── blueprint.html                 # script sinh
    ├── deps.rules
    ├── verified.stamp                 # do verify sinh, gitignore
    └── <feature>/brief.md, progress.md   # chỉ tier L
```

### Quy ước bước tiếp theo

Mọi skill v2 kết thúc bằng một dòng đề xuất bước tiếp theo, dựa trên **kết quả thực tế** của lần
chạy đó chứ không theo thứ tự cố định:

```text
**Tiếp theo:** `/ndv-verify` — vừa sửa 4 file .cs, chưa verify.
```

- Một đề xuất chính, ghi đúng lệnh kèm argument để chạy được ngay. Nếu kết quả rẽ nhánh, thêm tối
  đa một nhánh phụ.
- Chỉ đề xuất, không tự chạy bước sau khi bước đó cần người duyệt (criteria, L-brief, replan,
  commit).
- Không có bước hợp lý nào thì nói rõ "Task xong", không bịa bước.

| Skill xong với kết quả | Tiếp theo |
| --- | --- |
| `/ndv-blueprint`, `--check` còn finding blocking | Sửa theo finding, chạy lại `/ndv-blueprint --update` |
| `/ndv-blueprint`, đã approve | Viết hoặc cập nhật `.ndv/deps.rules` từ deps, rồi `/ndv-brief <feature>` |
| `/ndv-brief` (task M), có câu hỏi mở | Người trả lời câu hỏi mở |
| `/ndv-brief` (task M), criteria chờ duyệt | Người duyệt criteria → agent implement trong session này → `/ndv-verify` |
| `/ndv-brief` chế độ L, L-brief chờ duyệt | Người duyệt L-brief → session mới: `/ndv-brief <feature> M1` |
| `/ndv-verify` đỏ | Không đề xuất: agent tự sửa (Stop hook ép) |
| `/ndv-verify` đỏ cùng một lỗi lần thứ hai | `/ndv-lesson` |
| `/ndv-verify` xanh, task S | Người xem diff rồi commit |
| `/ndv-verify` xanh, task M hoặc milestone | Spawn `ndv-reviewer` |
| `ndv-reviewer` có finding severity cao | Sửa finding → `/ndv-verify` |
| `ndv-reviewer` flag blueprint chưa cập nhật | Sửa `.ndv/blueprint.json` → `ndv_blueprint.py --check` |
| `ndv-reviewer` sạch, task M | Người đọc audit rồi commit. Task xong |
| `ndv-reviewer` sạch, milestone còn tiếp | Cập nhật `progress.md` + commit → session mới: `/ndv-brief <feature> M<n+1>` |
| `ndv-reviewer` sạch, milestone cuối | Integration: full test (EditMode + PlayMode) + người playtest |
| Milestone phát hiện brief sai | Replan: agent đề xuất sửa `brief.md`, người duyệt |
| `/ndv-lesson` thêm check mới | `/ndv-verify` để chắc check mới không báo nhầm trên code hiện tại |

### Thay đổi so với v1

| v1 | v2 |
| --- | --- |
| GDD → blueprint → requirement.md (EARS) + specify.md → plan.md → tasks.md → implement | GDD → Blueprint (giữ nguyên) → Brief theo tier S/M/L |
| `/ndv-specify` + `/ndv-plan` | Gộp thành `/ndv-brief` |
| `/ndv-tasks` | Bỏ; task L chia milestone trong L-brief |
| `/ndv-implement` (sau gate plan + tasks) | Implement trong cùng session với brief |
| `/ndv-sync` | Bỏ; thay bằng `progress.md` và cập nhật blueprint trong cùng commit |
| Đọc toàn bộ host rules + kit rules trước khi viết | Rules có scope + check bằng máy |
| Người đọc spec + report để đối chiếu | `/ndv-verify` + reviewer subagent |

**Thành phần v1: giữ hay bỏ.** Nguyên tắc: bỏ mọi thứ v2 không cần.

| Thành phần v1 | Quyết định | Lý do / thay bằng |
| --- | --- | --- |
| `/ndv-blueprint`, `ndv_blueprint.py`, `blueprint-template.html` | Giữ | Tầng blueprint của v2 |
| `module-architect` | Giữ, rút gọn | Chỉ còn Mode blueprint + blueprint-review; bỏ mapping, register, full, module, brownfield |
| `ndv_check.py` | Giữ một phần | Chuyển về `ndv-blueprint/scripts/`, chỉ giữ phần `ndv_blueprint.py` import |
| `/ndv-blueprint-to-spec` + `workflow.js` | Bỏ | Brief thay cho requirement + specify |
| `/ndv-module-matrix` + `modules.json` | Bỏ | `blueprint.json` là module map duy nhất; bỏ luôn `check_matrix` trong `ndv_blueprint.py` |
| `/ndv-specify`, `/ndv-plan`, `/ndv-tasks`, `/ndv-implement`, `/ndv-sync` | Bỏ | `/ndv-brief` + implement cùng session + `progress.md` |
| `/ndv-audit-code` | Bỏ | `ndv-reviewer` mỗi task; audit toàn codebase khi cần thì prompt trực tiếp |
| `/ndv-audit-fix` + `audit-fixer` | Bỏ | Findings sửa ngay trong session, verify loop ép xanh |
| `/ndv-onboard` | Bỏ | `/ndv-blueprint --code-graph` cho project đã có code |
| `spec-writer` | Bỏ | Không còn spec |
| `module-implementer` | Bỏ | Implement ở main session để giữ context |
| `code-auditor` | Thay | Vai FINDER + severity R7 + anti-hallucination thành `ndv-reviewer`; bỏ VERIFIER, PLAN-REVIEWER |
| `requirement`, `specify`, `plan`, `tasks` templates | Bỏ | Thay bằng brief, L-brief, progress templates |
| `ndvkit.config.json` | Sửa | `ndvRoot: ".ndv"`; bỏ `matrixRoot`, `specsRoot`, `auditReportRoot`; cập nhật `verifyNote` khi có test |

**Lộ trình chuyển đổi:**

1. Thêm Stop hook + `/ndv-verify` (compile + console + check-deps; test khi project có).
2. Đổi config sang `ndvRoot: ".ndv"`, chuyển blueprint hiện có vào `.ndv/`, rút gọn
   `module-architect`, tách `ndv_check.py`. Viết `deps.rules` từ deps trong blueprint.
3. Thêm `/ndv-brief` + templates, rồi xóa các skill, agent và template bị bỏ ở bảng trên.
4. Tách rules hiện có: phần kiểm được bằng máy thành check, phần còn lại thành rules có scope.
5. Thêm `ndv-reviewer` và `/ndv-lesson`.
6. Khi có module cần test: tách asmdef + test asmdef cho module đó, bật bước `run_tests`.

### Đo lường hiệu quả

v2 chỉ đáng giữ nếu thắng việc giao task thẳng trên task thật. Thử trên 5 task thật, so v2 với giao
task thẳng theo ba chỉ số:

| Chỉ số | Cách đo |
| --- | --- |
| Token mỗi task | Usage của session Claude Code |
| Thời gian đến khi xanh | Từ prompt đầu đến lần `/ndv-verify` pass |
| Số vòng sửa lại ý | Số lần người phải nói "không phải ý mình" |

Nếu v2 không thắng ở chỉ số thứ ba, brief chưa đủ sắc. Chỗ cần chỉnh là acceptance criteria, không
phải thêm bước.


## Cài đặt

Repo này CHÍNH LÀ nội dung của folder `<project>/.claude/ndvkit/` — không có bước "copy
vào" nào khác ngoài clone đúng chỗ.

```bash
# chạy tại repo root của project game
git clone https://github.com/eternalTornado/ndv-kit.git .claude/ndvkit
```

Tên folder đích PHẢI là `ndvkit` (không phải `ndv-kit`): mọi skill/agent trong kit đọc
hardcode path `.claude/ndvkit/ndvkit.config.json` và `.claude/ndvkit/rules/**`, và script
Activation (xem mục [Activation](#activation)) symlink theo `../ndvkit/skills/` — sai tên
folder làm vỡ cả hai.

Sau khi clone:

1. Sửa `ndvkit.config.json` theo project (xem [Config per-project](#config-per-project--ndvkitconfigjson)).
2. Chạy Activation để kit được Claude Code auto-discover.

## Rule precedence (áp cho MỌI agent + skill trong kit)

1. `.claude/rules/**` + `CLAUDE.md` của project host (auto-load) **thắng** mọi thứ trong kit khi mâu thuẫn, và thắng cả plan.md / tasks.md. Host vs kit không bao giờ là conflict cần hỏi user. Host rule mô tả trạng thái project phải đúng ngay; repo lệch thì dừng và hỏi, không ghi chú rồi đi tiếp.
2. Domain nào host KHÔNG define → dùng **kit default rules** tại [`rules/`](rules/README.md) (`kitRulesRoot`) — bộ rules đầy đủ `Shared/` + `Unity/` + `Server/`, project-agnostic. Sửa rule = ghi entry vào [`rules/CHANGELOG.md`](rules/CHANGELOG.md). Project mới có thể copy nguyên folder này vào `.claude/rules/` để auto-load (adopt = tự define rules riêng từ đó).
3. Trước khi viết artifact/code, đọc rules theo thứ tự trên: toàn bộ host rules trước (không lọc theo lens hay tên file), rồi kit rules per lens (`/ndv-audit-code` Step 0) cho coding style, naming, architecture, pitfalls, security/authority, id allocation.
4. Baseline AI behavior là R1–R10, chia hai file theo đối tượng đọc — SoT duy nhất, không
   restate ở đây: [`rules/Shared/ai-discipline.md`](rules/Shared/ai-discipline.md) (worker
   core, mọi sub-agent đọc) giữ R1, R2, R3, R4, R5, R7; còn
   [`rules/Shared/ai-discipline-session.md`](rules/Shared/ai-discipline-session.md) (main
   session) giữ R6, R8, R9, R10 + Exception/Enforcement/Governance. Đánh số R không đổi khi
   chia file.

   - R1 — Tool-first, verify before claim
   - R2 — Say "I don't know"
   - R3 — Cite every claim
   - R4 — Literal quote khi adopt source
   - R5 — No AI-invented content trong artifact
   - R6 — Follow chosen workflow, direct answer
   - R7 — Finding + Evidence + Impact format
   - R8 — Proposals: grounded, holistic, concise
   - R9 — Single Source of Truth (cite-back)
   - R10 — Enterprise register

## Pipeline

```text
<gddRoot>/**                                 (Design — nguồn duy nhất của gameplay truth)
  │  /ndv-blueprint     [agent: module-architect — Mode blueprint (author) + Mode blueprint-review (reviewer độc lập);
  │                      script ndv_blueprint.py: --code-graph · --check · --render · --approve]
  │     gate (user): decision mở (boundary / gdd-gap / foundation / project) + approve report
  ▼
<matrixRoot>/blueprint.json + blueprint.html (module blueprint: band Foundation tái dùng cross-project ở trên cùng →
  │                                           Layer 1..n, core loop band, deps consumer → owner; html script sinh)
  │  /ndv-blueprint-to-spec  [Workflow: skills/ndv-blueprint-to-spec/workflow.js — scope layer → analyze → author → specify per layer;
  │                          agent: spec-writer, module-architect + verifier nội bộ workflow;
  │                          script ndv_check.py --spec-seq cấp folder <NNN>_<MODULE> theo thứ tự layer]
  │     gate A (user): module mapping + GDD gap        gate B (user): EARS ambiguity + contract-gap
  ▼
<matrixRoot>/modules.json + modules.md       (json = data SoT do agent ghi; md = human view + status, script sinh, zero agent cost; waterfall layers L0 → Ln)
<specsRoot>/<NNN>_<MODULE>/requirement.md    (NNN = thứ tự implement; EARS, Source cite GDD anchor / decision: / contract:)
<specsRoot>/<NNN>_<MODULE>/specify.md        (clarified + Given/When/Then — chỉ ghi khi zero NEEDS CLARIFICATION)
  │  /ndv-plan     ─▶ plan.md                (technical design + plan review [code-auditor vai PLAN-REVIEWER], GATE: user approve)
  │  /ndv-tasks    ─▶ tasks.md               (ordered tasks, GATE: user approve)
  │  /ndv-implement           [agent: module-implementer + code-auditor FINDER phase review]  (chỉ chạy sau khi plan+tasks approved)
  ▼
<codeRoots>/<Module>/                        (code)
  │  /ndv-audit-code module <MODULE>  [agent: code-auditor]
  ▼
<auditReportRoot>/<MODULE>-<date>.md

/ndv-specify <MODULE>  — clarify/update MỘT module ngoài workflow: clarification đã Defer, sửa requirement,
                         spec-fix (--from-audit), contract back-propagation. Không còn là bước của luồng chính.
/ndv-module-matrix     — maintenance: re-sync toàn bộ từ spec + code (không arg), re-derive một <module-id>
                         từ code, --verify.
/ndv-sync — delta orchestrator: GDD/spec/module/code đổi → detect drift → route đúng step downstream
            (chain: GDD → blueprint.json → requirement.md (+ modules.json) → specify.md → plan.md → tasks.md → code).
Mọi skill trong kit đều IDEMPOTENT (create-or-update): chạy lại trên artifact đã tồn tại = update mode.

Estate-wide audit (ngoài vòng per-module — CÙNG skill /ndv-audit-code, khác scope):
/ndv-audit-code current [<path>]    [agent: code-auditor]  → <auditReportRoot>/code/<YYYYMMDD-HHMM>-current.md
/ndv-audit-code changes vs-<base>   [agent: code-auditor]  → <auditReportRoot>/code/<YYYYMMDD-HHMM>-changes.md
Mọi mode (module/current/changes) chấm theo cùng 5 lens: patterns · naming · data · spec · ui
(ui = reskin/UI-toolkit standards, theo rules `ui-theming` + `naming-ui-toolkit`).

Fix-flow (đóng vòng audit — nhận report của /ndv-audit-code, mọi mode):
/ndv-audit-fix        [agent: audit-fixer]      → parse findings unchecked → triage (code-fix / spec-fix → /ndv-specify <MODULE> --from-audit <report> / register-fix → /ndv-module-matrix <MODULE> / defer) → fix → verify → tick + Triage vào report

Brownfield adoption (add kit vào project giữa chừng):
/ndv-onboard status       script ndv_check.py --inventory + drift checks của /ndv-sync Phase 1 (không spawn agent) → onboard report
/ndv-onboard matrix       [agent: module-architect — Mode brownfield]                                                → modules.json
/ndv-onboard reverse-doc  [agent: spec-writer — Mode as-built]                                                       → requirement as-built (origin: reverse-engineered)
```

### `/ndv-blueprint` — kiến trúc module trước spec

`/ndv-blueprint [<gdd-folder>] [--update]` — đọc TOÀN BỘ GDD folder, đề xuất bộ module theo
[`rules/Shared/module-design.md`](rules/Shared/module-design.md) (MD rules), ghi
`<matrixRoot>/blueprint.json` (data SoT, `module-architect` Mode blueprint) → script check (schema,
id, cycle, Foundation không depend `game`, cite GDD + code, đối chiếu modules.json) → reviewer độc lập
(`module-architect` Mode blueprint-review) → script render `blueprint.html` theo
[`templates/blueprint-template.html`](templates/blueprint-template.html) (format service blueprint:
band core loop có stage highlight → band Foundation → Layer 1..n, node tag NEW / EXTEND / REBUILD /
EXISTING, edge consumer → owner kèm contract, bảng module / deps / decisions / out of scope) → gate
user: trả lời decision mở rồi approve (`ndv_blueprint.py --approve`, chỉ skill set). Brownfield:
`--code-graph` đưa SCC của code hiện có cho architect — mỗi SCC là MỘT module tới khi user chọn
rebuild. Sau approve, `/ndv-blueprint-to-spec` lấy blueprint làm catalog module (Mode mapping không đề
xuất module ngoài blueprint) và `spec-writer` viết module band `foundation` bằng từ vựng
project-agnostic.

### `/ndv-blueprint-to-spec` — theo step, từng layer của blueprint

`/ndv-blueprint-to-spec <blueprint-path> [<gdd-path-or-feature-name>] [--update]` — gọi skill = user opt-in
multi-agent orchestration (Workflow tool). `<blueprint-path>` = `blueprint.json` đã approve (hoặc
folder chứa nó; không arg → `<matrixRoot>/blueprint.json`); GDD của run mặc định = `gddSources` của
blueprint, argument GDD chỉ thu hẹp. Steps: blueprint gate (`ndv_blueprint.py --check`) → **scope
gate LUÔN hỏi**: một / nhiều layer (Foundation row, Layer k, hoặc module id) hay toàn bộ layer →
scout → stage `analyze` MỘT lần cho cả scope (`moduleFilter` = module của scope) → Gate A → per
layer theo thứ tự Foundation → Layer 1..n: cấp folder `<NNN>_<MODULE>` (`ndv_check.py --spec-seq`) →
`author` → Gate B → `specify` → checkpoint (tiếp layer kế / dừng). Owner viết trước consumer nên
contract tới layer dưới đã có requirement.md và số folder của owner nhỏ hơn. MỘT script
`skills/ndv-blueprint-to-spec/workflow.js` chạy theo `args.stage`; main session hỏi user giữa các stage
(AskUserQuestion), agent trong workflow không hỏi. `--update` (hoặc tự nhận khi requirement.md đã
list GDD file trong `gdd-sources`, hoặc requirement.md legacy có `tdd-source` trỏ TDD cite GDD file
đó) = update mode.

| Stage | Làm gì | Gate sau stage |
|---|---|---|
| `analyze` | analyst trích technical item từng chunk GDD (literal + cite) → quoteVerifier refute quote → critic completeness (MỘT vòng re-analyze) → `module-architect` Mode mapping (read-only) đề xuất module mapping | **Gate A**: user confirm/sửa module mapping + trả lời GDD gap (answer → `decision:`; Defer → `NEEDS CLARIFICATION` giữ trong requirement.md, module đó không có specify.md run này) |
| `author` | `spec-writer` Mode forward viết requirement.md (batch ≤3 module) → verifier adversarial → Mode fix ≤2 vòng; reconciler link `Owner FR`/`Consumer FR` hoặc `contract-gap`; `module-architect` Mode register ghi modules.json (layer + cycle); ambiguity reviewer per module. Skill refresh `status` bằng script | **Gate B**: EARS ambiguity; mỗi `contract-gap` (add FR / stopgap / withdraw — semantics của `/ndv-specify` Phase 4); defect / coverage miss còn lại; matrix cycle = blocking |
| `specify` | `spec-writer` Mode back-propagation per target module → Mode compose-specify per module (ghi answer ngược vào requirement.md, compose specify.md chỉ khi zero marker) → verifier → Mode fix ≤2 vòng. Có `withdraw` Contract surface row → skill spawn `module-architect` Mode register lại consumer đó (`plannedDeps` re-derive theo row hiện tại). Refresh `status` lại | — |

Output: `<matrixRoot>/modules.json` (+ `modules.md` do script render), `<specsRoot>/<NNN>_<MODULE>/requirement.md`
+ `specify.md`. Report per module: FR/NFR, specify.md đã ghi hay marker còn mở, `decision:` mới,
contract-gap đóng/mở + follow-up, layer table + cycle, model dùng per stage. Workflow tool không có →
chạy cùng các stage bằng Task theo prompt/schema trong `workflow.js`. Never commit.

## Quy ước chung của kit

- **Skill gọi skill**: chỉ `/ndv-sync` Phase 3 và `/ndv-implement` Phase 3 được invoke skill
  khác (qua tool Skill) — mọi skill còn lại chỉ NÊU TÊN command cho user tự chạy, không tự gọi.
- **Status refresh + `modules.md`** luôn do script `ndv_check.py` làm, không bao giờ spawn
  agent chỉ để refresh status hay render lại view.
- **Spec folder đánh số kiểu migration** (golang-migrate `-seq`): `<specsRoot>/<NNN>_<MODULE>/`
  (vd `docs/Specs/001_SaveService/`), `NNN` = thứ tự implement. Số cấp `max + 1` lúc folder được
  tạo, không bao giờ đánh lại hay tái dùng. `/ndv-blueprint-to-spec` tạo folder theo thứ tự layer
  (Foundation → Layer 1..n, trong layer theo id) nên owner có số nhỏ hơn consumer: `ls <specsRoot>`
  = thứ tự implement. Chỉ script cấp số (`ndv_check.py --spec-seq <MODULE...> --write`, module
  theo đúng thứ tự đó); agent nhận path folder qua dispatch, không tự tạo hay đổi số. Folder của
  một module = field `spec` của entry modules.json, chưa có thì Glob `<specsRoot>/*_<MODULE>/`.
  Module id (FR prefix, modules.json, audit report) không mang số.
- **Resume, không respawn** (agent spawn qua Task): orchestrator resume lại đúng agent instance
  đang chạy (sang phase kế, có câu trả lời user, gặp compile error) — chỉ spawn instance mới khi
  harness không resume được, agent tự báo context gần hết, hoặc escalate theo
  [Model routing](#model-routing).
- **Protocol sống trong file agent**, spawn prompt chỉ mang role · scope · paths — skill không
  restate contract của agent.
- **Một agent, nhiều vai**: `module-architect` Mode blueprint-review, `code-auditor` VERIFIER và
  `code-auditor` PLAN-REVIEWER là instance MỚI của cùng agent (độc lập với author/finder) — ngoại lệ
  có chủ đích của "resume, không respawn".
- **Workflow**: chỉ `/ndv-blueprint-to-spec` chạy Workflow tool; agent trong workflow không hỏi user —
  main session hỏi giữa các stage.
- **Model**: mỗi spawn line của skill ghi model cụ thể (`model: <x>` trong Task call) theo
  [Model routing](#model-routing).

## Config per-project — `ndvkit.config.json`

| Key | Ý nghĩa | Bắt buộc |
|---|---|---|
| `gddRoot` | Folder chứa GDD | ✔ |
| `matrixRoot` | Folder output ModuleMatrix | ✔ |
| `specsRoot` | Folder chứa per-module spec artifacts | ✔ |
| `auditReportRoot` | Folder output audit report | ✔ |
| `codeRoots` | Danh sách folder chứa module code (điền theo project — vd Unity: `Assets/...`) | ✔ |
| `contractsDoc` | Path registry contract cross-module của project (nếu có) | optional |
| `rulesRoot` | Folder rules của host (mặc định `.claude/rules`) | optional |
| `kitRulesRoot` | Bộ rules default của kit (mặc định `.claude/ndvkit/rules`) — fallback khi host im lặng | optional |
| `verifyNote` | Cách verify compile/build của project (vd "Unity MCP", "dotnet build", "npm test") — skill implement/audit dùng | optional |
| `templates` | Folder template của kit | ✔ |

Giá trị đang ship trong `ndvkit.config.json` của repo này là VÍ DỤ của một project Unity
(Windows, verify qua MCP for Unity — xem `verifyNote`) — mọi key phải sửa theo project
trước khi chạy bất kỳ skill nào. `verifyNote` là hook host-tooling DUY NHẤT mà kit định
nghĩa để verify build/compile; kit không tự có test runner hay build script riêng.

## Checker script

`skills/ndv-blueprint/scripts/ndv_blueprint.py` — Python 3.8+, stdlib only, import resolver của
`ndv_check.py`: `--code-graph` (SCC type-reference dưới `codeRoots`), `--check` (exit 1 = blocking),
`--render` (sinh `blueprint.html`, deterministic), `--approve <date>` (từ chối khi còn blocking /
decision mở). Dùng bởi `/ndv-blueprint`, `/ndv-blueprint-to-spec` Phase 0, `/ndv-module-matrix` Phase 2,
`/ndv-sync` Phase 1.

`skills/ndv-sync/scripts/ndv_check.py` — Python 3.8+, stdlib only, chạy từ repo root của host:
`python3 .claude/ndvkit/skills/ndv-sync/scripts/ndv_check.py` (Windows: `python` / `py -3`). Đọc
`ndvkit.config.json` + `<matrixRoot>/modules.json`, không hard-code project. Checks mặc định
(`doc-cite`/`code-cite`/`contract-gap`/`deps`, `--reanchor`) dùng bởi `/ndv-sync` (Phase 1,
`--reanchor`) và `/ndv-implement` (cite sweep). Host không có Python: skill fallback sang Grep
thủ công — kết quả tương đương nhưng không lặp lại được.

Bốn mode standalone (mỗi mode chạy một mình, bỏ qua các cite check ở trên):

| Mode | Làm gì | Dùng bởi |
|---|---|---|
| `--refresh-status [MODULE ...]` | dry-run derive field `status` (§Status lifecycle của `/ndv-module-matrix`); kèm `--write` mới apply vào `modules.json` + render lại `modules.md` | `/ndv-module-matrix` Phase 2; `/ndv-blueprint-to-spec` (sau stage author + specify), `/ndv-plan` on Approve, `/ndv-tasks` on Approve, `/ndv-implement` Phase 3, `/ndv-audit-code module` (mọi verdict), `/ndv-onboard` matrix/reverse-doc |
| `--render` | sinh `<matrixRoot>/modules.md` từ `modules.json`, không đụng `status` | gọi tay khi chỉ cần re-render view |
| `--inventory` | estate counts theo root + bảng coverage artifact per module (code/matrix/requirement/specify/plan/tasks/audit) | `/ndv-onboard status` |
| `--spec-seq [MODULE ...]` | spec folder theo thứ tự implement (`dirs` = map id → folder) + finding `unnumbered` / `seq-order` (owner số lớn hơn consumer) / `seq-duplicate` / `id-duplicate`. Có `MODULE` → cấp số kế tiếp theo thứ tự argument cho module chưa có folder đánh số; không argument → đánh số folder cũ không số theo layer modules.json. Kèm `--write` mới apply: mkdir, hoặc rename + rewrite reference `<specsRoot>/<MODULE>` trong specs / modules.json / CLAUDE.md / rules (cite-only edit) | `/ndv-blueprint-to-spec` (Step 1, 5a), `/ndv-onboard` status / reverse-doc, `/ndv-sync` Phase 1 |

## Layout

```text
.claude/ndvkit/
├── README.md
├── .gitignore                 # ignore .DS_Store, __pycache__/
├── ndvkit.config.json         # giá trị per-project — file DUY NHẤT cần sửa khi đem sang project khác
├── rules/                     # KIT DEFAULT RULES — Shared/ + Unity/ + Server/ (xem rules/README.md)
│   ├── CHANGELOG.md           # amendment history của rules (rationale + migration) — body rule chỉ giữ current state
│   └── Shared/ Unity/ Server/
├── agents/                    # frontmatter: name/description/tools/model (default — xem Model routing) — copy, không link
│   ├── spec-writer.md
│   ├── module-architect.md
│   ├── module-implementer.md
│   ├── code-auditor.md        # FINDER/VERIFIER/PLAN-REVIEWER worker (roles, không phải ba agent)
│   └── audit-fixer.md         # fix-executor worker cho /ndv-audit-fix
├── skills/                    # <name>/SKILL.md
│   ├── ndv-blueprint/
│   │   ├── SKILL.md
│   │   └── scripts/ndv_blueprint.py   # --code-graph · --check · --render · --approve
│   ├── ndv-blueprint-to-spec/
│   │   ├── SKILL.md
│   │   └── workflow.js        # Workflow script — args.stage: analyze | author | specify; hằng MODEL
│   ├── ndv-module-matrix/     # maintenance: full re-sync | <module-id> | --verify
│   ├── ndv-specify/
│   ├── ndv-plan/
│   ├── ndv-tasks/
│   ├── ndv-implement/
│   ├── ndv-audit-code/        # skill audit DUY NHẤT: module <id>... | module --all | current [<path>] | changes vs-<base>
│   ├── ndv-audit-fix/         # fix-flow: apply Fix từ audit findings (WRITE trên code)
│   ├── ndv-onboard/           # brownfield adoption: status / matrix / reverse-doc
│   └── ndv-sync/
│       └── scripts/ndv_check.py   # checker deterministic: doc-cite · code-cite · contract-gap · deps · --reanchor · --refresh-status · --render · --inventory · --spec-seq
└── templates/
    ├── blueprint-template.html      # view của blueprint.json — ndv_blueprint.py --render inject data
    ├── requirement-template.md      # EARS patterns + Source forms + Data & constants
    ├── specify-template.md
    ├── plan-template.md
    └── tasks-template.md
```

## Skills

Thứ tự theo pipeline. `argument-hint` khớp frontmatter của từng `SKILL.md`.

| Skill | Arguments | Agent spawn | Output | Gate/ghi chú |
|---|---|---|---|---|
| `/ndv-blueprint` | `[<gdd-folder>] [--update]` | `module-architect` (Mode blueprint + instance riêng Mode blueprint-review) | `<matrixRoot>/blueprint.json` + `blueprint.html` (script render) | gate: decision mở + defect review còn lại + approve (`--approve`, chỉ skill set); check blocking chặn gate (trừ `approval-void` / `matrix-band-violation` — hỏi ở gate); never commit |
| `/ndv-blueprint-to-spec` | `<blueprint-path> [<gdd-path-or-feature-name>] [--update]` | Workflow `workflow.js` (scope layer → stage analyze một lần → author → specify per layer): `spec-writer`, `module-architect` + verifier nội bộ workflow | `<matrixRoot>/modules.json` (+ `modules.md` script render) + `<specsRoot>/<NNN>_<MODULE>/requirement.md` + `specify.md` | gate A: module mapping + GDD gap; gate B: EARS ambiguity + `contract-gap`; specify.md chỉ ghi khi zero marker; matrix cycle = blocking; never commit |
| `/ndv-module-matrix` | `[<module-id>] [--verify]` | `module-architect` | `<matrixRoot>/modules.json` (data SoT) + `modules.md` (script render) | maintenance (luồng chính register qua `/ndv-blueprint-to-spec`): không arg = full re-sync từ spec + code; `<module-id>` = re-derive từ code; layer không cycle; derive `status` bằng script (§Status lifecycle) |
| `/ndv-specify` | `<module-id> [--from-audit <report-path> [--ids F-001,F-002]]` | — (inline, compose theo `spec-writer` §Mode compose-specify; `spec-writer` cho contract back-propagation) | `<specsRoot>/<NNN>_<MODULE>/specify.md` | single-module: clarification đã Defer, sửa requirement, contract back-propagation (`contract-gap` nêu trong report); owner của spec-fix; zero `NEEDS CLARIFICATION` |
| `/ndv-plan` | `<module-id>` | `code-auditor` (vai PLAN-REVIEWER) | `<specsRoot>/<NNN>_<MODULE>/plan.md` | plan review trước gate; user approve (AskUserQuestion) |
| `/ndv-tasks` | `<module-id>` | — (inline) | `<specsRoot>/<NNN>_<MODULE>/tasks.md` | user approve (AskUserQuestion); Prerequisites derive từ specify |
| `/ndv-implement` | `<module-id> [--phase <n>] [--continue]` | `module-implementer`; `code-auditor` (vai FINDER, phase review) | code dưới `<codeRoots>/<Module>/` | hard gate: plan + tasks approved; Prerequisites thỏa; write scope = `paths` của module (scope check sau mỗi phase); phase review lens patterns + spec trên file đổi, candidate ≥ medium quay lại implementer; cite sweep khi close |
| `/ndv-audit-code` | `[module <module-id>... \| module --all \| current [<path>] \| changes vs-<base>]` | `code-auditor` (vai FINDER + vai VERIFIER) | mode `module` → `<auditReportRoot>/<MODULE>-<yyyy-mm-dd>.md`; mode `current`/`changes` → `<auditReportRoot>/code/<YYYYMMDD-HHMM>-<mode>.md` | READ-ONLY; mode `module` refresh `status` bằng script sau mọi verdict |
| `/ndv-audit-fix` | `[<report-path> \| latest [code \| module <module-id>]] [--ids F-001,F-002] [--severity <min>]` | `audit-fixer` | code fixes + tick/`## Triage` trong report | never commit; triage code-fix / spec-fix → `/ndv-specify --from-audit` / register-fix → `/ndv-module-matrix` / defer; severity filter theo taxonomy đóng R7 |
| `/ndv-onboard` | `[status \| matrix \| reverse-doc [<module-id>...]] (omit = hỏi)` | — (inline; `status` = script only; `matrix` → `module-architect` Mode brownfield; `reverse-doc` → `spec-writer` Mode as-built) | `onboard-<date>.md` / `modules.json` + `modules.md` / requirement as-built | reverse-doc: clarifications chờ owner |
| `/ndv-sync` | `[gdd\|matrix\|spec\|code <target>] [--check-only] [--reanchor]` | — (inline, route tới skill khác) | impact table (không tự tạo artifact riêng) | gate downstream không bị bypass; cite-only edit không void approval |

## Agents

`code-auditor` được `/ndv-audit-code` spawn hai lần với vai khác nhau trong cùng một run: FINDER (quét,
emit candidate) rồi VERIFIER (instance độc lập, cố refute candidate). `/ndv-plan` spawn vai
PLAN-REVIEWER (chấm plan.md trước gate), `/ndv-implement` spawn vai FINDER cho phase review — các vai
của MỘT agent, không phải nhiều agent. Cột Model: frontmatter (default) → routing per dispatch theo
[Model routing](#model-routing).

| Agent | Model | Tools | Dùng bởi | Quyền trên code |
|---|---|---|---|---|
| `spec-writer` | `opus` → sonnet cho back-propagation, cite-only | Read, Glob, Grep, Write, Edit | `/ndv-blueprint-to-spec` (workflow: Mode forward / fix / back-propagation / compose-specify); `/ndv-onboard` (`reverse-doc`, Mode as-built); `/ndv-specify` (contract back-propagation); `/ndv-sync` (cite-only) | READ-ONLY (ghi requirement.md + specify.md, không ghi code) |
| `module-architect` | `opus` → fable cho blueprint-review; sonnet cho register, `<module-id>`, `--verify` fallback | Read, Glob, Grep, Write, Edit, Bash | `/ndv-blueprint` (Mode blueprint, Mode blueprint-review read-only); `/ndv-blueprint-to-spec` (workflow: Mode mapping read-only, Mode register); `/ndv-module-matrix`; `/ndv-onboard` (`matrix`, Mode brownfield) | READ-ONLY (ghi `blueprint.json`, `modules.json`) |
| `module-implementer` | `sonnet` → opus MỘT lần sau vòng compile-fix fail thứ 2 của một phase | Read, Glob, Grep, Write, Edit, Bash | `/ndv-implement` | WRITE |
| `code-auditor` | `opus` → sonnet cho FINDER chỉ có lens `naming` và/hoặc `ui`, và FINDER phase review | Read, Grep, Glob, Bash | `/ndv-audit-code` — vai FINDER và vai VERIFIER; `/ndv-plan` — vai PLAN-REVIEWER; `/ndv-implement` — vai FINDER phase review | READ-ONLY |
| `audit-fixer` | `sonnet` → opus cho cluster chứa finding `blocker`/`critical`; MỘT lần thử opus sau giới hạn verify 2 vòng | Read, Glob, Grep, Write, Edit, Bash | `/ndv-audit-fix` | WRITE |

## Model routing

SoT của nguyên tắc chọn model cho sub-agent của kit. Frontmatter `model:` của agent = default; mỗi
spawn line của skill ghi model cụ thể (`model: <x>` trong Task call) — skill không cần đọc README;
workflow của `/ndv-blueprint-to-spec` dùng hằng `MODEL` đầu `workflow.js`.

- **Judgment** — đọc source mơ hồ để quyết định (phân tích GDD, ranh giới module, viết EARS,
  acceptance criteria, verdict adversarial trên audit finding) → `opus` / `fable`.
- **Bounded** — thực thi input đã chốt (implement task đã approve, apply Fix có sẵn,
  back-propagate row đã chọn, register mapping đã confirm, verify máy móc quote/cite/ID, lens
  checklist naming/ui) → `sonnet`.
- **Escalate** — worker bounded đã hết vòng fix → lên MỘT tier cho MỘT lần retry (instance mới
  mang delta lỗi) trước khi báo user.
- `haiku` không dùng mặc định.
- Override: host đổi model theo role (workflow: `args.models`; Task spawn: spawn line của skill);
  prefix `[model]` hoặc rule trong `CLAUDE.md` của host thắng (§Rule precedence mục 1) — kể cả rule
  model toàn cục của user (`~/.claude/CLAUDE.md`): rule ép MỘT model cho mọi sub-agent làm routing
  này mất hiệu lực; muốn dùng routing thì rule đó phải ghi ngoại lệ cho `/ndv-*`.

| Agent / role | Frontmatter | Routing per dispatch |
|---|---|---|
| `spec-writer` | `opus` | forward / as-built / compose-specify / fix: opus · back-propagation, cite-only: sonnet |
| `module-architect` | `opus` | blueprint / mapping / full / brownfield: opus · blueprint-review: fable (instance độc lập, khác model author) · register, `<module-id>`, `--verify` fallback: sonnet |
| `module-implementer` | `sonnet` | sonnet; sau vòng compile-fix fail thứ 2 của một phase → MỘT instance mới trên opus mang error delta trước khi báo user |
| `code-auditor` | `sonnet` | VERIFIER, PLAN-REVIEWER: opus · FINDER: opus, trừ FINDER chỉ có lens `naming` và/hoặc `ui`, và FINDER phase review của `/ndv-implement` → sonnet |
| `audit-fixer` | `sonnet` | sonnet; cluster chứa finding `blocker`/`critical` → opus; hết giới hạn verify 2 vòng → MỘT lần thử mới trên opus trước khi báo user |
| workflow `/ndv-blueprint-to-spec` | — | hằng `MODEL`: analyst, critic, mapper, writer, fixer, reconciler, ambiguity, composer → opus · quoteVerifier, verifier, register, backprop → sonnet |

## Activation

Folder đích phải là `.claude/ndvkit` (đã clone đúng chỗ theo mục [Cài đặt](#cài-đặt)) —
hai script dưới đây giả định điều đó. Kit ở trạng thái STAGED trong `.claude/ndvkit/` —
Claude Code chỉ auto-discover `.claude/agents/` và `.claude/skills/`. Khi muốn kích hoạt:

```powershell
# Windows — junction skills (giữ ndvkit là SoT), copy agents
Get-ChildItem .claude\ndvkit\skills -Directory | ForEach-Object {
  New-Item -ItemType Junction -Path ".claude\skills\$($_.Name)" -Target $_.FullName
}
Get-ChildItem .claude\ndvkit\agents\*.md | Copy-Item -Destination .claude\agents\
```

```bash
# macOS/Linux — symlink
for d in .claude/ndvkit/skills/*/; do ln -s "../ndvkit/skills/$(basename "$d")" ".claude/skills/$(basename "$d")"; done
cp .claude/ndvkit/agents/*.md .claude/agents/
```

Gỡ kích hoạt: xóa junction/symlink/file copy — `.claude/ndvkit/` vẫn nguyên.

Agents đọc rules qua `kitRulesRoot` trong config, không qua link tương đối — copy sang
`.claude/agents/` không làm vỡ tham chiếu.

**Migrate từ kit bản cũ**: Activation chỉ tạo mới, không dọn rác — host đã activate một bản kit
cũ phải tự xóa link/copy của skill/agent đã bị bỏ trước khi re-run Activation ở trên:

```bash
# bản còn tầng TDD
rm -f .claude/skills/ndv-gdd-to-tdd .claude/skills/ndv-tdd-to-spec .claude/agents/tdd-writer.md
# bản còn audit tách hai skill
rm -f .claude/skills/ndv-audit-module .claude/skills/ndv-audit-standards
rm -f .claude/agents/module-auditor.md .claude/agents/standards-auditor.md .claude/agents/onboarder.md
# bản còn tên /ndv-gdd-to-spec (nay /ndv-blueprint-to-spec)
rm -f .claude/skills/ndv-gdd-to-spec
```

(Windows: `Remove-Item` tương ứng.) Sau đó re-copy `agents/*.md` — agent file là COPY, không
phải link, nên bản cũ trong `.claude/agents/` không tự cập nhật theo kit.

Host có artifact từ pipeline còn TDD (`/ndv-sync`, `/ndv-onboard status` báo `legacy-tdd`):

1. Mỗi feature có requirement.md còn cite TDD (`tdd-source`, Source trỏ `<tddRoot>/…`):
   `/ndv-blueprint-to-spec <blueprint-path> <Feature> --update` — stage author re-cite sang GDD anchor mà TDD đó quote
   (`spec-writer` §Mode forward); câu TDD mang `decision:` → giữ decision (kèm GDD anchor của
   section; GDD nay có literal cho điểm đó → cite GDD), không hỏi lại; không có GDD cite lẫn
   decision → `NEEDS CLARIFICATION`. Không còn row nào cite TDD → xóa `tdd-source`; specify.md
   compose lại ở stage specify khi module hết marker.
2. requirement.md `origin: reverse-engineered` còn cite TDD (as-built của `/ndv-onboard reverse-doc`
   cũ — TDD `gdd-sources: N/A`, bước 1 không chạm): `/ndv-onboard reverse-doc <MODULE>` —
   `spec-writer` §Mode as-built re-cite về code symbol, xóa `tdd-source`.
3. `modules.json`: field `tdd` script bỏ qua; `plannedDepEvidence` trỏ `<tddRoot>` script KHÔNG còn
   check → trước bước 4 chạy `/ndv-module-matrix` (không arg, Mode full — chạm mọi entry): xóa `tdd`,
   re-cite/bỏ planned edge có evidence TDD theo Contract surface rows dưới `<specsRoot>`.
4. Mọi module của feature đã re-cite (bước 1–2) → user tự archive `<tddRoot>/<Feature>/` (kit không
   xóa).
5. Xóa key `tddRoot` khỏi `ndvkit.config.json` (`ndv_check.py` bỏ qua key này nếu còn).

Host có spec folder không số `<specsRoot>/<MODULE>/` (`/ndv-sync`, `/ndv-onboard status` báo
`unnumbered`):

1. Folder của module đã bỏ khỏi blueprint → user archive / xóa trước, để không chiếm số.
2. `python3 .claude/ndvkit/skills/ndv-sync/scripts/ndv_check.py --spec-seq` — dry-run: plan đánh
   số theo layer modules.json rồi id (topological nên owner trước consumer). Có blueprint đã approve
   hoặc layer modules.json chưa thật (register chưa chạy hết) → truyền id theo thứ tự layer của
   blueprint (`ndv_blueprint.py --check --json` → `modules`: Foundation row → Layer n, trong layer
   theo id): `--spec-seq <id...>`.
3. Cùng lệnh kèm `--write`: rename folder + rewrite mọi reference `<specsRoot>/<MODULE>` trong specs /
   modules.json / CLAUDE.md / rules (render lại modules.md). Thay đổi chỉ là path nên là cite-only
   edit (`/ndv-sync` §Cite-only edit): không void approval của plan/tasks.

## Artifact ownership & gates

| Artifact | Owner tạo/update | Gate trước bước sau |
|---|---|---|
| `<specsRoot>/<NNN>_<MODULE>/` (folder) | `ndv_check.py --spec-seq <MODULE...> --write`, gọi bởi `/ndv-blueprint-to-spec` Step 5a và `/ndv-onboard reverse-doc` — số không bao giờ đổi sau khi cấp | — |
| `<matrixRoot>/blueprint.json` (+ `blueprint.html` view) | `/ndv-blueprint` (`module-architect` Mode blueprint ghi data; `ndv_blueprint.py` render + set approval) | **user approve** (AskUserQuestion) — mọi decision có `chosen`, script `--check` không blocking; `/ndv-blueprint-to-spec` hỏi trước khi chạy không có blueprint approve |
| `<matrixRoot>/` (`modules.json` data SoT + `modules.md` view) | `/ndv-blueprint-to-spec` (stage author, `module-architect` Mode register) + `/ndv-module-matrix` (maintenance) ghi `modules.json` — field `status` là giá trị DERIVE bằng script theo §Status lifecycle (`implemented`, yêu cầu `tasks.md` hết task `- [ ]` → `planned` → `specced` → `proposed`); refresh bằng `ndv_check.py --refresh-status --write`, không spawn agent | gate A (user confirm module mapping) trước register; layer assignment không cycle |
| `<specsRoot>/<NNN>_<MODULE>/requirement.md` | `/ndv-blueprint-to-spec` (forward); `/ndv-specify` (write-back answer, contract back-propagation); `/ndv-onboard reverse-doc` (as-built) | gate B (user): EARS ambiguity + `contract-gap` trước khi compose specify.md; GDD gap Defer ở gate A → `NEEDS CLARIFICATION` còn trong file, chờ `/ndv-specify` |
| `<specsRoot>/<NNN>_<MODULE>/specify.md` | `/ndv-blueprint-to-spec` (stage specify); `/ndv-specify` (single-module, kể cả spec-fix qua `--from-audit`) | zero `NEEDS CLARIFICATION` còn sót; `contract-gap` còn mở nêu trong report |
| `<specsRoot>/<NNN>_<MODULE>/plan.md` | `/ndv-plan` | **user approve** (AskUserQuestion) |
| `<specsRoot>/<NNN>_<MODULE>/tasks.md` | `/ndv-tasks` | **user approve** (AskUserQuestion) |
| code | `/ndv-implement` (write scope = `paths` của module trong modules.json) | build/compile sạch + audit pass |
| `<auditReportRoot>/<MODULE>-<date>.md` | `/ndv-audit-code module` | — |
| `<auditReportRoot>/code/<run>/` | `/ndv-audit-code current \| changes` (READ-ONLY, estate-wide) | — |
| code fixes + tick/Triage trong audit report | `/ndv-audit-fix` | compile sạch theo `verifyNote` + Evidence formula hết hit |
| `<auditReportRoot>/onboard-<date>.md` + `modules.json`/`modules.md`/requirement as-built | `/ndv-onboard` | reverse-doc: clarifications chờ owner trước khi vào forward flow |

Lưu ý collision: nếu project host đã có spec flow khác đang own artifact cùng tên trong
`<specsRoot>/<NNN>_<MODULE>/` (vd `plan.md`, `tasks.md`), coi artifact đó là LEGACY INPUT
(đọc để không mâu thuẫn) và hỏi user chọn flow trước khi ghi đè.
