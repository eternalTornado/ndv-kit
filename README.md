# ndvkit

Bộ harness cho Claude Code trên dự án Unity: skills, agents, hooks và script để agent làm đúng ý,
tự kiểm chứng, và tốn ít token hơn việc giao task thẳng. Kit portable — mọi giá trị per-project nằm ở
`ndvkit.config.json`, mọi convention per-project defer về `.claude/rules/**` của project host.

Token tiêu vào kiểm chứng kết quả, không tiêu vào viết tài liệu:

1. **Ít artifact, nhiều verification.** Artifact cấp project duy nhất là blueprint.
2. **Intent chốt bằng acceptance criteria kiểm được.** Người duyệt criteria khoảng 1 phút, không duyệt spec.
3. **Workflow theo độ lớn task** (S / M / L).
4. **Giữ context liền mạch.** Brief và implement chạy cùng session; chỉ tách session ở ranh giới milestone.
5. **Ép bằng máy trước, nhắc bằng chữ sau.** Hook, `check-deps.sh`, check script, test.
6. **Audit bằng máy trước, người sau.** Người đọc diff stat, bảng criteria và tối đa 5 finding.
7. **Mỗi lỗi lặp lại thành một check mới** (`/ndv-lesson`).
8. **Skill nào xong cũng đề xuất bước tiếp theo.**

## 1. Cài đặt

Repo này CHÍNH LÀ nội dung của `<project>/.claude/ndvkit/`:

```bash
# tại repo root của project game
git clone https://github.com/eternalTornado/ndv-kit.git .claude/ndvkit
```

Tên folder phải là `ndvkit`: skill, agent, hook đều đọc `.claude/ndvkit/…`. Sau khi clone:

1. Sửa `.claude/ndvkit/ndvkit.config.json` (mục 2).
2. Kích hoạt skills và agents (Claude Code chỉ auto-discover `.claude/skills/` và `.claude/agents/`):

   ```bash
   # macOS/Linux — symlink skills, copy agents
   mkdir -p .claude/skills .claude/agents
   for d in .claude/ndvkit/skills/*/; do ln -sfn "../ndvkit/skills/$(basename "$d")" ".claude/skills/$(basename "$d")"; done
   cp .claude/ndvkit/agents/*.md .claude/agents/
   ```

   ```powershell
   # Windows — junction skills, copy agents
   Get-ChildItem .claude\ndvkit\skills -Directory | ForEach-Object {
     New-Item -ItemType Junction -Path ".claude\skills\$($_.Name)" -Target $_.FullName -Force
   }
   Copy-Item .claude\ndvkit\agents\*.md .claude\agents\
   ```

3. Gộp hooks của `.claude/ndvkit/templates/settings.json` vào `.claude/settings.json` của project:
   Stop hook `require-verify.sh` và SessionStart hook `gdd-drift.sh`.
4. Thêm `.ndv/verified.stamp` vào `.gitignore` của project. Phần còn lại của `.ndv/` (blueprint,
   deps.rules, brief, progress, impact, checks) commit cùng code.
5. `CLAUDE.md` của project nên dưới 100 dòng: project map, lệnh build/test, vài nguyên tắc không được
   vi phạm. Rules chi tiết để ở `.claude/rules/*.md` có `paths:` frontmatter.

Cần `python3` (3.8+, stdlib) cho `ndv_blueprint.py`, `bash` cho hook và `check-deps.sh` (Windows: Git
Bash). Agent file là COPY: cập nhật kit thì copy lại `agents/*.md`.

## 2. Config — `ndvkit.config.json`

| Key | Ý nghĩa |
| --- | --- |
| `gddRoot` | Folder GDD (nguồn gameplay). Kit không giả định format GDD. |
| `ndvRoot` | Folder artifact của kit, mặc định `.ndv`. |
| `codeRoots` | Folder code mà blueprint, `--code-graph` và review xét. |
| `rulesRoot`, `kitRulesRoot` | Rules của host (thắng) và rules mặc định của kit. |
| `templates` | Template của kit. |
| `verifyNote` | Cách verify của project: MCP server, thứ tự lệnh, fallback. `/ndv-verify` làm đúng theo nó. |

## 3. Input và output

**Input:** GDD (`gddRoot`) · code hiện có (`codeRoots`) · rules (host + kit) · yêu cầu từng task ·
Unity Editor + MCP để compile và chạy test.

**Output** (tất cả trong `<ndvRoot>/` trừ code):

| File | Sinh bởi | Ghi chú |
| --- | --- | --- |
| `blueprint.json` + `blueprint.html` | `/ndv-blueprint` | Kiến trúc module; html do script render |
| `deps.rules` | `/ndv-blueprint`, `/ndv-lesson` | Folder nào không được dùng namespace nào |
| `gdd-ref` | `/ndv-blueprint` (approve), `/ndv-impact` (đóng vòng) | Commit GDD mà code đang phản ánh |
| `<feature>/brief.md` + `progress.md` | `/ndv-brief --L` | Chỉ task L |
| `impact/<date>.md` | `/ndv-impact` | Bảng tác động khi GDD đổi |
| `checks/*.sh` | `/ndv-lesson` | Check máy của project, `/ndv-verify` chạy |
| `verified.stamp` | `/ndv-verify` | Stop hook đọc; gitignore |
| Code + test | Main session | Task S/M không sinh file tài liệu nào; brief nằm trong session |

Finding của reviewer trả trong chat, không ghi file.

## 4. Workflow

### Tier

| Tier | Khi nào | Workflow | Người can thiệp |
| --- | --- | --- | --- |
| S | 1–2 file, yêu cầu rõ | Prompt thẳng; Stop hook ép `/ndv-verify` | Xem diff |
| M | Feature nhỏ, nhiều file | `/ndv-brief "<task>"` → duyệt → implement cùng session → verify → review | Duyệt criteria ~1 phút + đọc report |
| L | Hệ thống mới, nhiều ngày | `/ndv-brief <feature> --L` → các milestone, mỗi cái như một task M → integration | Duyệt L-brief 10–15 phút, mỗi milestone 3–5 phút, playtest |

Bắt đầu project: `/ndv-blueprint` (đọc GDD + code, đề xuất module, gate, approve → `deps.rules`, `gdd-ref`).

### Task M — `/ndv-brief "<task>"`

1. Explore subagent đọc code liên quan (main context gọn).
2. Brief một trang trong chat: Goal · Acceptance criteria 3–7 dòng kiểm được (kèm "Kiểm bằng") · Sẽ
   sửa · Test thay đổi · Out of scope · Câu hỏi mở.
3. Người duyệt criteria — điểm chặn sai ý rẻ nhất.
4. Implement ngay trong session đó.
5. `/ndv-verify` tới khi xanh.
6. `ndv-reviewer` (context sạch) đối chiếu diff với criteria, blueprint, rules.
7. Report: diff stat · bảng criteria · finding còn lại → người commit.

### Task L

```text
/ndv-brief <feature> --L ─► người duyệt L-brief (Decisions + milestones, rủi ro cao trước)
   ─► session mới: /ndv-brief <feature> M1 ─► mini-brief ─► implement ─► verify ─► review
        ─► progress.md + commit ─► session mới: M2 … ─► milestone cuối: /ndv-verify --full + playtest
   brief sai giữa chừng ─► /ndv-brief <feature> --replan (agent dừng, người duyệt)
```

Mỗi milestone vừa một session, kết thúc ở compile được + test xanh + commit được. `progress.md` là bộ
nhớ giữa các session; agent không đọc lại lịch sử session trước.

### GDD thay đổi — `/ndv-impact`

```text
GDD đổi ─► /ndv-impact: diff từ gdd-ref → bảng tác động theo module ─► người duyệt bảng
   ─► từng dòng: text (bỏ qua) · value → S · behavior → M · new → blueprint + M/L · structural → /ndv-blueprint --update + L
   ─► xong / hoãn hết dòng ─► /ndv-impact cập nhật gdd-ref
```

SessionStart hook nhắc khi GDD lệch `gdd-ref`. Feature L đang dở mà bị ảnh hưởng → Replan. Test cũ khóa
hành vi cũ: brief phải liệt kê test đổi và vì sao; reviewer flag mọi test đổi ngoài danh sách.

## 5. Verify loop và hooks

`/ndv-verify` (theo `verifyNote`):

1. Compile + console qua Unity MCP. Không verify được → không xanh.
2. `scripts/check-deps.sh` theo `<ndvRoot>/deps.rules`.
3. Mỗi `<ndvRoot>/checks/*.sh`.
4. Unity Test Framework qua `run_tests`: toàn bộ EditMode mỗi lần (regression); PlayMode khi brief yêu
   cầu hoặc `--full`. Project chưa có test asmdef → bỏ bước này và báo rõ.
5. Acceptance criteria ✅ / ❌ / ⚪ (⚪ = máy không kiểm được, để reviewer và người).
6. Xanh hết → `touch <ndvRoot>/verified.stamp`.

**Stop hook** (`hooks/require-verify.sh`): còn file `.cs` (đã sửa hoặc mới) mới hơn stamp → exit 2,
agent phải verify và sửa trước khi kết thúc. Lần dừng thứ hai trong cùng chuỗi luôn qua
(`stop_hook_active`), nên không loop vô hạn. **SessionStart hook** (`hooks/gdd-drift.sh`): in một dòng
nhắc `/ndv-impact` khi GDD đổi kể từ `gdd-ref`.

**Test runner** là Unity Test Framework (NUnit). EditMode cho logic C# thuần (nhanh), PlayMode cho
lifecycle, scene, physics (chậm). Test nằm trong test asmdef, mà asmdef không reference được
`Assembly-CSharp`: module có logic cần test phải có asmdef riêng.

## 6. Ép dependency

Namespace một mình không chặn gì: không có asmdef thì mọi script compile chung vào `Assembly-CSharp`.

| Mức | Cách | Độ chính xác |
| --- | --- | --- |
| 1 | `deps.rules` + `check-deps.sh` (grep, bỏ comment và dòng `namespace`) | Bắt phần lớn; lọt khi dùng alias hoặc `using` cha |
| 2 | Architecture test (Mono.Cecil) hoặc Roslyn analyzer severity Error | Resolve type thật |
| 3 | asmdef dần dần, bắt đầu từ `Core` | Compile fail khi vi phạm; thêm compile incremental |

`/ndv-blueprint` dẫn `deps.rules` từ blueprint sau khi approve (phần sinh ở trên `# manual`, phần tự
thêm ở dưới). Vi phạm lọt qua check → `/ndv-lesson` nâng mức.

## 7. Rules

Thứ tự ưu tiên: `.claude/rules/**` + `CLAUDE.md` của host **thắng** mọi thứ trong kit; domain host
không define → kit rules ở `rules/` (`Shared/` + `Unity/` + `Server/`, xem `rules/README.md`). Mọi
rule kit trừ `Shared/constitution.md` và `Shared/ai-discipline*.md` có `paths:` frontmatter, nên chỉ
nạp khi chạm file liên quan. AI behavior R1–R10: `rules/Shared/ai-discipline.md` (worker) và
`rules/Shared/ai-discipline-session.md` (main session).

`/ndv-lesson`: lỗi agent lặp lại → ưu tiên một check máy (dòng `deps.rules`, EditMode test, hoặc
`<ndvRoot>/checks/<tên>.sh`); chỉ khi không kiểm được bằng máy mới thêm MỘT dòng vào rule host có
`paths:` đúng scope. Không sửa rule của kit.

## 8. Skills và agents

| Thành phần | Arguments | Làm gì |
| --- | --- | --- |
| `/ndv-blueprint` | `[<gdd-folder>] [--update]` | GDD + code → `blueprint.json` + `.html`, gate, approve, `deps.rules`, `gdd-ref` |
| `/ndv-brief` | `"<task>"` · `<feature> --L` · `<feature> M<n>` · `<feature> --replan` | Task M trọn vòng; L-brief; một milestone; replan |
| `/ndv-verify` | `[--playmode] [--full]` | Compile, deps, checks, test, criteria → stamp |
| `/ndv-impact` | `[--base <commit>]` | GDD đổi → bảng tác động → dòng nào chạy tier nào; đóng vòng cập nhật `gdd-ref` |
| `/ndv-lesson` | `["<lỗi lặp lại>"]` | Lỗi lặp lại → check máy hoặc một dòng rule |
| `module-architect` | Mode blueprint · blueprint-review | Viết và review blueprint (hai instance độc lập) |
| `ndv-reviewer` | — | Read-only, context sạch, tối đa 5 finding có severity R7 |

Model: `module-architect` opus (review blueprint: fable), `ndv-reviewer` sonnet, phần còn lại chạy model
của phiên. Host override (rule model trong `CLAUDE.md`) thắng.

## 9. Quy ước bước tiếp theo

Mọi skill kết thúc bằng một dòng đề xuất bước tiếp theo, dựa trên **kết quả thực tế** của lần chạy:

```text
**Tiếp theo:** `/ndv-verify` — vừa sửa 4 file .cs, chưa verify.
```

- Một đề xuất chính, ghi đúng lệnh kèm argument; tối đa một nhánh phụ.
- Chỉ đề xuất, không tự chạy bước cần người duyệt (criteria, L-brief, replan, bảng impact, commit).
- Không còn bước hợp lý thì nói rõ "Task xong".

| Skill xong với kết quả | Tiếp theo |
| --- | --- |
| `/ndv-blueprint`, còn blocking / decision mở | Trả lời gate → `/ndv-blueprint --update` |
| `/ndv-blueprint` approved, có vi phạm dependency | `/ndv-brief "sửa vi phạm dependency: <module>"` |
| `/ndv-blueprint` approved, sạch | `/ndv-brief "<task>"` hoặc `/ndv-brief <feature> --L` |
| `/ndv-brief` (M), chờ duyệt | Người duyệt criteria → agent implement → `/ndv-verify` |
| `/ndv-brief --L`, chờ duyệt | Người duyệt L-brief → session mới: `/ndv-brief <feature> M1` |
| `/ndv-verify` đỏ | Không đề xuất: agent tự sửa (Stop hook ép) |
| `/ndv-verify` đỏ cùng một lỗi lần thứ hai | `/ndv-lesson` |
| `/ndv-verify` chưa verify được | Mở Unity Editor / bật MCP → `/ndv-verify` |
| `/ndv-verify` xanh, task S | Người xem diff rồi commit |
| `/ndv-verify` xanh, task M hoặc milestone | `ndv-reviewer` (bước review của `/ndv-brief`) |
| `ndv-reviewer` có finding `high` trở lên | Sửa → `/ndv-verify` → review lại |
| `ndv-reviewer` báo blueprint cần cập nhật | `/ndv-blueprint --update` |
| Review sạch, task M | Người đọc report rồi commit. Task xong |
| Review sạch, milestone còn tiếp | `progress.md` + commit → session mới: `/ndv-brief <feature> M<n+1>` |
| Review sạch, milestone cuối | `/ndv-verify --full` + người playtest |
| Milestone phát hiện brief sai | `/ndv-brief <feature> --replan` |
| SessionStart báo GDD đổi | `/ndv-impact` |
| `/ndv-impact`, bảng chờ duyệt | Người duyệt bảng |
| `/ndv-impact` duyệt, có dòng structural / new | `/ndv-blueprint --update` |
| `/ndv-impact` duyệt, dòng pending kế tiếp | S: làm thẳng · M: `/ndv-brief "I-<n>: …"` · L: `/ndv-brief <feature> --L` |
| `/ndv-impact`, hết dòng pending | `/ndv-impact` đóng vòng (cập nhật `gdd-ref`) |
| `/ndv-lesson` thêm check | `/ndv-verify` (check mới không báo nhầm) |

## 10. Layout

```text
.claude/ndvkit/
├── README.md
├── ndvkit.config.json
├── hooks/
│   ├── require-verify.sh        # Stop hook
│   └── gdd-drift.sh             # SessionStart hook
├── scripts/
│   └── check-deps.sh
├── agents/
│   ├── module-architect.md      # Mode blueprint + blueprint-review
│   └── ndv-reviewer.md
├── skills/
│   ├── ndv-blueprint/
│   │   ├── SKILL.md
│   │   └── scripts/
│   │       ├── ndv_blueprint.py # --code-graph · --check · --render · --approve
│   │       └── ndv_common.py    # config, cite, code index (tách từ ndv_check.py của v1)
│   ├── ndv-brief/SKILL.md
│   ├── ndv-verify/SKILL.md
│   ├── ndv-impact/SKILL.md
│   └── ndv-lesson/SKILL.md
├── rules/                       # kit default rules — Shared/ Unity/ Server/ + CHANGELOG.md
└── templates/
    ├── blueprint-template.html
    ├── brief-template.md
    ├── l-brief-template.md
    ├── progress-template.md
    ├── impact-template.md
    └── settings.json            # hooks để gộp vào .claude/settings.json
```

## 11. Migrate từ v1

v1 là pipeline GDD → blueprint → requirement (EARS) + specify → plan → tasks → implement → audit. Trạng
thái cuối cùng của v1 nằm ở commit `61b7f4a`.

1. Gỡ link/copy của skill và agent đã bỏ trong project:

   ```bash
   rm -f .claude/skills/ndv-{blueprint-to-spec,module-matrix,specify,plan,tasks,implement,sync,audit-code,audit-fix,onboard}
   rm -f .claude/agents/{spec-writer,module-implementer,code-auditor,audit-fixer}.md
   ```

   rồi chạy lại bước kích hoạt (mục 1).
2. Config: thêm `ndvRoot`, bỏ `matrixRoot`, `specsRoot`, `auditReportRoot`, `contractsDoc`; cập nhật
   `verifyNote` nếu project có test.
3. Chuyển `<matrixRoot>/blueprint.json` sang `<ndvRoot>/blueprint.json`, chạy
   `/ndv-blueprint --update` để render lại, dẫn `deps.rules` và ghi `gdd-ref`.
4. `modules.json`, `docs/Specs/**`, audit report: kit không đọc nữa. Giữ làm lịch sử hoặc archive.
5. Gộp hooks (mục 1 bước 3) và gitignore stamp.

## 12. Đo lường hiệu quả

v2 chỉ đáng giữ nếu thắng việc giao task thẳng trên task thật. Thử trên 5 task thật, so theo:

| Chỉ số | Cách đo |
| --- | --- |
| Token mỗi task | Usage của session Claude Code |
| Thời gian đến khi xanh | Từ prompt đầu đến lần `/ndv-verify` xanh |
| Số vòng sửa lại ý | Số lần người phải nói "không phải ý mình" |

Nếu v2 không thắng ở chỉ số thứ ba, brief chưa đủ sắc: chỉnh acceptance criteria, không thêm bước.
