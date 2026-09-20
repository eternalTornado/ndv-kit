# ndvkit — GDD → TDD → ModuleMatrix → Spec (EARS) → Implement pipeline

Bộ agents + skills PORTABLE cho vòng đời feature game project, format theo
[Claude-Code-Game-Studios](https://github.com/Donchitos/Claude-Code-Game-Studios) `.claude/`.
Kit không chứa reference cứng vào một project cụ thể — mọi giá trị per-project nằm ở
`ndvkit.config.json`, mọi convention per-project defer về `.claude/rules/**` của project host.

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

1. `.claude/rules/**` + `CLAUDE.md` của project host (auto-load) **thắng** mọi thứ trong kit khi mâu thuẫn.
2. Domain nào host KHÔNG define → dùng **kit default rules** tại [`rules/`](rules/README.md) (`kitRulesRoot`) — bộ rules đầy đủ `Shared/` + `Unity/` + `Server/`, project-agnostic. Sửa rule = ghi entry vào [`rules/CHANGELOG.md`](rules/CHANGELOG.md). Project mới có thể copy nguyên folder này vào `.claude/rules/` để auto-load (adopt = tự define rules riêng từ đó).
3. Trước khi viết artifact/code, đọc rules liên quan theo thứ tự trên (coding style, naming, architecture, pitfalls, security/authority, id allocation).
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
<gddRoot>/**                                (Design — nguồn duy nhất của gameplay truth)
  │  /ndv-gdd-to-tdd          [agent: tdd-writer]
  ▼
<tddRoot>/<Feature>/tdd.md                  (chỉ technical concern, mọi claim cite GDD anchor)
  │  /ndv-module-matrix       [agent: module-architect]
  ▼
<matrixRoot>/modules.json + modules.md      (json = data SoT do agent ghi; md = human view + status, script sinh, zero agent cost; waterfall layers L0 → Ln)
  │  /ndv-tdd-to-spec         [agent: spec-writer]
  ▼
<specsRoot>/<MODULE>/requirement.md         (EARS format, trace về TDD + GDD)
  │  /ndv-specify  ─▶ specify.md            (EARS clarified — mọi ambiguity resolved)
  │  /ndv-plan     ─▶ plan.md               (technical design, GATE: user approve)
  │  /ndv-tasks    ─▶ tasks.md              (ordered tasks, GATE: user approve)
  │  /ndv-implement           [agent: module-implementer]  (chỉ chạy sau khi plan+tasks approved)
  ▼
<codeRoots>/<Module>/                       (code)
  │  /ndv-audit-code module <MODULE>  [agent: code-auditor]
  ▼
<auditReportRoot>/<MODULE>-<date>.md

/ndv-sync — delta orchestrator: GDD/TDD/spec/module đổi → detect drift → route đúng step downstream.
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
/ndv-onboard reverse-doc  [agent: tdd-writer + spec-writer]                                                          → TDD + requirement as-built (origin: reverse-engineered)
```

## Quy ước chung của kit

- **Skill gọi skill**: chỉ `/ndv-sync` Phase 3 và `/ndv-implement` Phase 3 được invoke skill
  khác (qua tool Skill) — mọi skill còn lại chỉ NÊU TÊN command cho user tự chạy, không tự gọi.
- **Status refresh + `modules.md`** luôn do script `ndv_check.py` làm, không bao giờ spawn
  agent chỉ để refresh status hay render lại view.
- **Resume, không respawn**: orchestrator resume lại đúng agent instance đang chạy (sang phase
  kế, có câu trả lời user, gặp compile error) — chỉ spawn instance mới khi harness không resume
  được, hoặc agent tự báo context gần hết.
- **Protocol sống trong file agent**, spawn prompt chỉ mang role · scope · paths — skill không
  restate contract của agent.

## Config per-project — `ndvkit.config.json`

| Key | Ý nghĩa | Bắt buộc |
|---|---|---|
| `gddRoot` | Folder chứa GDD | ✔ |
| `tddRoot` | Folder output TDD | ✔ |
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

`skills/ndv-sync/scripts/ndv_check.py` — Python 3.8+, stdlib only, chạy từ repo root của host:
`python3 .claude/ndvkit/skills/ndv-sync/scripts/ndv_check.py` (Windows: `python` / `py -3`). Đọc
`ndvkit.config.json` + `<matrixRoot>/modules.json`, không hard-code project. Checks mặc định
(`doc-cite`/`code-cite`/`contract-gap`/`deps`, `--reanchor`) dùng bởi `/ndv-sync` (Phase 1,
`--reanchor`) và `/ndv-implement` (cite sweep). Host không có Python: skill fallback sang Grep
thủ công — kết quả tương đương nhưng không lặp lại được.

Ba mode standalone (mỗi mode chạy một mình, bỏ qua các cite check ở trên):

| Mode | Làm gì | Dùng bởi |
|---|---|---|
| `--refresh-status [MODULE ...]` | dry-run derive field `status` (§Status lifecycle của `/ndv-module-matrix`); kèm `--write` mới apply vào `modules.json` + render lại `modules.md` | `/ndv-module-matrix` Phase 2; `/ndv-tdd-to-spec`, `/ndv-plan` on Approve, `/ndv-tasks` on Approve, `/ndv-implement` Phase 3, `/ndv-audit-code module` (mọi verdict), `/ndv-onboard` matrix/reverse-doc |
| `--render` | sinh `<matrixRoot>/modules.md` từ `modules.json`, không đụng `status` | gọi tay khi chỉ cần re-render view |
| `--inventory` | estate counts theo root + bảng coverage artifact per module (code/matrix/TDD/requirement/specify/plan/tasks/audit) | `/ndv-onboard status` |

## Layout

```text
.claude/ndvkit/
├── README.md
├── .gitignore                 # ignore .DS_Store, __pycache__/
├── ndvkit.config.json         # giá trị per-project — file DUY NHẤT cần sửa khi đem sang project khác
├── rules/                     # KIT DEFAULT RULES — Shared/ + Unity/ + Server/ (xem rules/README.md)
│   ├── CHANGELOG.md           # amendment history của rules (rationale + migration) — body rule chỉ giữ current state
│   └── Shared/ Unity/ Server/
├── agents/                    # frontmatter: name/description/tools/model — copy, không link
│   ├── tdd-writer.md
│   ├── module-architect.md
│   ├── spec-writer.md
│   ├── module-implementer.md
│   ├── code-auditor.md        # FINDER/VERIFIER worker cho /ndv-audit-code (roles, không phải hai agent)
│   └── audit-fixer.md         # fix-executor worker cho /ndv-audit-fix
├── skills/                    # <name>/SKILL.md
│   ├── ndv-gdd-to-tdd/
│   ├── ndv-module-matrix/
│   ├── ndv-tdd-to-spec/
│   ├── ndv-specify/
│   ├── ndv-plan/
│   ├── ndv-tasks/
│   ├── ndv-implement/
│   ├── ndv-audit-code/        # skill audit DUY NHẤT: module <id>... | module --all | current [<path>] | changes vs-<base>
│   ├── ndv-audit-fix/         # fix-flow: apply Fix từ audit findings (WRITE trên code)
│   ├── ndv-onboard/           # brownfield adoption: status / matrix / reverse-doc
│   └── ndv-sync/
│       └── scripts/ndv_check.py   # checker deterministic: doc-cite · code-cite · contract-gap · deps · --reanchor · --refresh-status · --render · --inventory
└── templates/
    ├── tdd-template.md
    ├── requirement-template.md      # EARS patterns + rule
    ├── specify-template.md
    ├── plan-template.md
    └── tasks-template.md
```

## Skills

Thứ tự theo pipeline. `argument-hint` khớp frontmatter của từng `SKILL.md`.

| Skill | Arguments | Agent spawn | Output | Gate/ghi chú |
|---|---|---|---|---|
| `/ndv-gdd-to-tdd` | `<gdd-path-or-feature-name> [--update]` | `tdd-writer` | `<tddRoot>/<Feature>/tdd.md` | user resolve `NEEDS CLARIFICATION` |
| `/ndv-module-matrix` | `[<tdd-feature> \| <module-id>] [--verify]` | `module-architect` | `<matrixRoot>/modules.json` (data SoT) + `modules.md` (script render) | layer không cycle; derive `status` bằng script (§Status lifecycle) |
| `/ndv-tdd-to-spec` | `<tdd-feature> [<module-id>...]` | `spec-writer` | `<specsRoot>/<MODULE>/requirement.md` | TDD phải hết `NEEDS CLARIFICATION` trong scope |
| `/ndv-specify` | `<module-id> [--from-audit <report-path> [--ids F-001,F-002]]` | — (inline; `spec-writer` cho contract back-propagation) | `<specsRoot>/<MODULE>/specify.md` | zero `NEEDS CLARIFICATION`; contract back-propagation (`contract-gap` nêu trong report); owner của spec-fix |
| `/ndv-plan` | `<module-id>` | — (inline) | `<specsRoot>/<MODULE>/plan.md` | user approve (AskUserQuestion) |
| `/ndv-tasks` | `<module-id>` | — (inline) | `<specsRoot>/<MODULE>/tasks.md` | user approve (AskUserQuestion); Prerequisites derive từ specify |
| `/ndv-implement` | `<module-id> [--phase <n>] [--continue]` | `module-implementer` | code dưới `<codeRoots>/<Module>/` | hard gate: plan + tasks approved; Prerequisites thỏa; write scope = `paths` của module (scope check sau mỗi phase); cite sweep khi close |
| `/ndv-audit-code` | `[module <module-id>... \| module --all \| current [<path>] \| changes vs-<base>]` | `code-auditor` (vai FINDER + vai VERIFIER) | mode `module` → `<auditReportRoot>/<MODULE>-<yyyy-mm-dd>.md`; mode `current`/`changes` → `<auditReportRoot>/code/<YYYYMMDD-HHMM>-<mode>.md` | READ-ONLY; mode `module` refresh `status` bằng script sau mọi verdict |
| `/ndv-audit-fix` | `[<report-path> \| latest [code \| module <module-id>]] [--ids F-001,F-002] [--severity <min>]` | `audit-fixer` | code fixes + tick/`## Triage` trong report | never commit; triage code-fix / spec-fix → `/ndv-specify --from-audit` / register-fix → `/ndv-module-matrix` / defer; severity filter theo taxonomy đóng R7 |
| `/ndv-onboard` | `[status \| matrix \| reverse-doc [<module-id>...]] (omit = hỏi)` | — (inline; `status` = script only; `matrix` → `module-architect` Mode brownfield; `reverse-doc` → `tdd-writer` + `spec-writer`) | `onboard-<date>.md` / `modules.json` + `modules.md` / TDD + requirement as-built | reverse-doc: clarifications chờ owner |
| `/ndv-sync` | `[gdd\|tdd\|matrix\|spec\|code <target>] [--check-only] [--reanchor]` | — (inline, route tới skill khác) | impact table (không tự tạo artifact riêng) | gate downstream không bị bypass; cite-only edit không void approval |

## Agents

Tất cả 6 agent chạy `model: sonnet`. `code-auditor` được skill của nó spawn hai lần với vai
khác nhau trong cùng một run: FINDER (quét, emit candidate) rồi VERIFIER (instance độc lập,
cố refute candidate) — hai vai của MỘT agent, không phải hai agent.

| Agent | Model | Tools | Dùng bởi | Quyền trên code |
|---|---|---|---|---|
| `tdd-writer` | sonnet | Read, Glob, Grep, Write, Edit | `/ndv-gdd-to-tdd`; `/ndv-onboard` (`reverse-doc`) | READ-ONLY (ghi TDD, không ghi code) |
| `module-architect` | sonnet | Read, Glob, Grep, Write, Edit, Bash | `/ndv-module-matrix`; `/ndv-onboard` (`matrix`, Mode brownfield) | READ-ONLY (ghi `modules.json`) |
| `spec-writer` | sonnet | Read, Glob, Grep, Write, Edit | `/ndv-tdd-to-spec`; `/ndv-onboard` (`reverse-doc`); `/ndv-specify` (contract back-propagation) | READ-ONLY (ghi spec docs, không ghi code) |
| `module-implementer` | sonnet | Read, Glob, Grep, Write, Edit, Bash | `/ndv-implement` | WRITE |
| `code-auditor` | sonnet | Read, Grep, Glob, Bash | `/ndv-audit-code` — vai FINDER và vai VERIFIER | READ-ONLY |
| `audit-fixer` | sonnet | Read, Glob, Grep, Write, Edit, Bash | `/ndv-audit-fix` | WRITE |

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

**Migrate từ kit bản cũ**: host đã activate một bản kit từ trước khi audit gộp thành một skill
(còn `ndv-audit-module` và `ndv-audit-standards` riêng) phải tự xóa link/copy cũ — của cả hai
skill đó lẫn agent `module-auditor`/`standards-auditor`/`onboarder` — trước khi re-run
Activation ở trên; Activation chỉ tạo mới, không dọn rác:

```bash
rm -f .claude/skills/ndv-audit-module .claude/skills/ndv-audit-standards
rm -f .claude/agents/module-auditor.md .claude/agents/standards-auditor.md .claude/agents/onboarder.md
```

(Windows: `Remove-Item` tương ứng.) Sau đó re-copy `agents/*.md` — agent file là COPY, không
phải link, nên bản cũ trong `.claude/agents/` không tự cập nhật theo kit.

## Artifact ownership & gates

| Artifact | Owner tạo/update | Gate trước bước sau |
|---|---|---|
| `<tddRoot>/<Feature>/tdd.md` | `/ndv-gdd-to-tdd` | user review TDD |
| `<matrixRoot>/` (`modules.json` data SoT + `modules.md` view) | `/ndv-module-matrix` (ghi `modules.json`) — field `status` là giá trị DERIVE bằng script theo §Status lifecycle (`implemented`, yêu cầu `tasks.md` hết task `- [ ]` → `planned` → `specced` → `proposed`); refresh bằng `ndv_check.py --refresh-status --write`, không spawn agent | layer assignment không cycle |
| `<specsRoot>/<MODULE>/requirement.md` | `/ndv-tdd-to-spec` | — |
| `<specsRoot>/<MODULE>/specify.md` | `/ndv-specify` (kể cả spec-fix qua `--from-audit`) | zero `NEEDS CLARIFICATION` còn sót; `contract-gap` còn mở nêu trong report |
| `<specsRoot>/<MODULE>/plan.md` | `/ndv-plan` | **user approve** (AskUserQuestion) |
| `<specsRoot>/<MODULE>/tasks.md` | `/ndv-tasks` | **user approve** (AskUserQuestion) |
| code | `/ndv-implement` (write scope = `paths` của module trong modules.json) | build/compile sạch + audit pass |
| `<auditReportRoot>/<MODULE>-<date>.md` | `/ndv-audit-code module` | — |
| `<auditReportRoot>/code/<run>/` | `/ndv-audit-code current \| changes` (READ-ONLY, estate-wide) | — |
| code fixes + tick/Triage trong audit report | `/ndv-audit-fix` | compile sạch theo `verifyNote` + Evidence formula hết hit |
| `<auditReportRoot>/onboard-<date>.md` + `modules.json`/`modules.md`/TDD/requirement as-built | `/ndv-onboard` | reverse-doc: clarifications chờ owner trước khi vào forward flow |

Lưu ý collision: nếu project host đã có spec flow khác đang own artifact cùng tên trong
`<specsRoot>/<MODULE>/` (vd `plan.md`, `tasks.md`), coi artifact đó là LEGACY INPUT
(đọc để không mâu thuẫn) và hỏi user chọn flow trước khi ghi đè.
