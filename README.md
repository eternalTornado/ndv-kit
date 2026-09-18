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
4. Baseline AI behavior là R1–R10 trong [`rules/Shared/ai-discipline.md`](rules/Shared/ai-discipline.md) — SoT duy nhất, không restate ở đây:

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
<matrixRoot>/modules.json + index.html      (waterfall layers L0 → Ln; status derive; rootRel cho link)
  │  /ndv-tdd-to-spec         [agent: spec-writer]
  ▼
<specsRoot>/<MODULE>/requirement.md         (EARS format, trace về TDD + GDD)
  │  /ndv-specify  ─▶ specify.md            (EARS clarified — mọi ambiguity resolved)
  │  /ndv-plan     ─▶ plan.md               (technical design, GATE: user approve)
  │  /ndv-tasks    ─▶ tasks.md              (ordered tasks, GATE: user approve)
  │  /ndv-implement           [agent: module-implementer]  (chỉ chạy sau khi plan+tasks approved)
  ▼
<codeRoots>/<Module>/                       (code)
  │  /ndv-audit-module        [agent: module-auditor]
  ▼
<auditReportRoot>/<MODULE>-<date>.md

/ndv-sync — delta orchestrator: GDD/TDD/spec/module đổi → detect drift → route đúng step downstream.
Mọi skill trong kit đều IDEMPOTENT (create-or-update): chạy lại trên artifact đã tồn tại = update mode.

Estate-wide audit (ngoài vòng per-module):
/ndv-audit-code       [agent: code-auditor]      → <auditReportRoot>/code/<run>/       (progress·contract·quality·parity·duplication)
/ndv-audit-standards  [agent: standards-auditor] → <auditReportRoot>/standards/<run>/  (reskin token-hygiene·naming/MVC·element-name·reuse)

Fix-flow (đóng vòng audit — nhận report của CẢ BA audit skill):
/ndv-audit-fix        [agent: audit-fixer]      → parse findings unchecked → triage (code-fix / spec-fix → /ndv-sync / defer) → fix → verify → tick + Triage vào report

Brownfield adoption (add kit vào project giữa chừng):
/ndv-onboard          [agent: onboarder]         → (1) status-check → onboard report
                                                   (2) reverse module matrix từ code (DISCOVER → module-architect)
                                                   (3) reverse-doc: code as-built → TDD + requirement (origin: reverse-engineered)
```

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

## Layout

```text
.claude/ndvkit/
├── README.md
├── .gitignore                 # ignore .DS_Store
├── ndvkit.config.json         # giá trị per-project — file DUY NHẤT cần sửa khi đem sang project khác
├── rules/                     # KIT DEFAULT RULES — Shared/ + Unity/ + Server/ (xem rules/README.md)
│   ├── CHANGELOG.md           # amendment history của rules (rationale + migration) — body rule chỉ giữ current state
│   └── Shared/ Unity/ Server/
├── agents/                    # frontmatter: name/description/tools/model
│   ├── tdd-writer.md
│   ├── module-architect.md
│   ├── spec-writer.md
│   ├── module-implementer.md
│   ├── module-auditor.md      # audit MỘT module vs spec của nó
│   ├── code-auditor.md        # FINDER/VERIFIER worker cho /ndv-audit-code
│   ├── standards-auditor.md   # FINDER/VERIFIER worker cho /ndv-audit-standards
│   ├── audit-fixer.md         # fix-executor worker cho /ndv-audit-fix
│   └── onboarder.md           # SURVEY/DISCOVER worker cho /ndv-onboard (brownfield)
├── skills/                    # <name>/SKILL.md
│   ├── ndv-gdd-to-tdd/
│   ├── ndv-module-matrix/
│   ├── ndv-tdd-to-spec/
│   ├── ndv-specify/
│   ├── ndv-plan/
│   ├── ndv-tasks/
│   ├── ndv-implement/
│   ├── ndv-audit-module/
│   ├── ndv-audit-code/        # estate-wide code audit (finder→verifier protocol)
│   ├── ndv-audit-standards/   # estate-wide UI standardization-for-reskin audit
│   ├── ndv-audit-fix/         # fix-flow: apply Fix từ audit findings (WRITE trên code)
│   ├── ndv-onboard/           # brownfield adoption: status-check / reverse matrix / reverse-doc
│   └── ndv-sync/
└── templates/
    ├── tdd-template.md
    ├── requirement-template.md      # EARS patterns + rule
    ├── specify-template.md
    ├── plan-template.md
    ├── tasks-template.md
    └── module-matrix-template.html  # light theme, self-contained
```

## Skills

Thứ tự theo pipeline. `argument-hint` khớp frontmatter của từng `SKILL.md`.

| Skill | Arguments | Agent spawn | Output | Gate/ghi chú |
|---|---|---|---|---|
| `/ndv-gdd-to-tdd` | `<gdd-path-or-feature-name> [--update]` | `tdd-writer` | `<tddRoot>/<Feature>/tdd.md` | user resolve `NEEDS CLARIFICATION` |
| `/ndv-module-matrix` | `[<tdd-feature> \| <module-id>] [--render-only \| --verify]` | `module-architect` | `<matrixRoot>/modules.json` + `index.html` | layer không cycle; derive `status` (§Status lifecycle) |
| `/ndv-tdd-to-spec` | `<tdd-feature> [<module-id>...]` | `spec-writer` | `<specsRoot>/<MODULE>/requirement.md` | TDD phải hết `NEEDS CLARIFICATION` trong scope |
| `/ndv-specify` | `<module-id>` | — (inline) | `<specsRoot>/<MODULE>/specify.md` | zero `NEEDS CLARIFICATION` |
| `/ndv-plan` | `<module-id>` | — (inline) | `<specsRoot>/<MODULE>/plan.md` | user approve (AskUserQuestion) |
| `/ndv-tasks` | `<module-id>` | — (inline) | `<specsRoot>/<MODULE>/tasks.md` | user approve (AskUserQuestion) |
| `/ndv-implement` | `<module-id> [--phase <n>] [--continue]` | `module-implementer` | code dưới `<codeRoots>/<Module>/` | hard gate: plan + tasks approved |
| `/ndv-audit-module` | `<module-id> [--all]` | `module-auditor` | `<auditReportRoot>/<MODULE>-<yyyy-mm-dd>.md` (frontmatter `job: module-audit`, findings `- [ ] **F-NNN**`) | READ-ONLY trên code |
| `/ndv-audit-code` | `[current [<path>] \| changes vs-<base>]` | `code-auditor` (vai FINDER + vai VERIFIER) | `<auditReportRoot>/code/<run>/` | READ-ONLY, estate-wide |
| `/ndv-audit-standards` | `[current [<path>] \| changes vs-<base>]` | `standards-auditor` (vai FINDER + vai VERIFIER) | `<auditReportRoot>/standards/<run>/` | READ-ONLY, UI estate |
| `/ndv-audit-fix` | `[<report-path> \| latest [code\|standards\|module]] [--ids F-001,F-002] [--severity <min>]` | `audit-fixer` | code fixes + tick/`## Triage` trong report | never commit; severity filter theo taxonomy đóng R7 |
| `/ndv-onboard` | `[status \| matrix \| reverse-doc [<module-id>...]] (omit = hỏi)` | `onboarder` (+ `module-architect`/`tdd-writer`/`spec-writer` tuỳ option) | `onboard-<date>.md` / `modules.json` / TDD + requirement as-built | reverse-doc: clarifications chờ owner |
| `/ndv-sync` | `[gdd\|tdd\|matrix\|spec\|code <target>] [--check-only]` | — (inline, route tới skill khác) | impact table (không tự tạo artifact riêng) | gate downstream không bị bypass |

## Agents

Tất cả 9 agent chạy `model: sonnet`. `code-auditor` và `standards-auditor` được skill của
chúng spawn hai lần với vai khác nhau trong cùng một run: FINDER (quét, emit candidate) rồi
VERIFIER (instance độc lập, cố refute candidate).

| Agent | Model | Tools | Dùng bởi | Quyền trên code |
|---|---|---|---|---|
| `tdd-writer` | sonnet | Read, Glob, Grep, Write, Edit | `/ndv-gdd-to-tdd`; `/ndv-onboard` (Option 3, mode brownfield) | READ-ONLY (ghi TDD, không ghi code) |
| `module-architect` | sonnet | Read, Glob, Grep, Write, Edit, Bash | `/ndv-module-matrix`; `/ndv-onboard` (Option 2) | READ-ONLY (ghi modules.json/index.html) |
| `spec-writer` | sonnet | Read, Glob, Grep, Write, Edit | `/ndv-tdd-to-spec`; `/ndv-onboard` (Option 3) | READ-ONLY (ghi spec docs, không ghi code) |
| `module-implementer` | sonnet | Read, Glob, Grep, Write, Edit, Bash | `/ndv-implement` | WRITE |
| `module-auditor` | sonnet | Read, Glob, Grep, Bash, Write | `/ndv-audit-module` | READ-ONLY (file duy nhất ghi là report) |
| `code-auditor` | sonnet | Read, Grep, Glob, Bash | `/ndv-audit-code` — vai FINDER và vai VERIFIER | READ-ONLY |
| `standards-auditor` | sonnet | Read, Grep, Glob, Bash | `/ndv-audit-standards` — vai FINDER và vai VERIFIER | READ-ONLY |
| `audit-fixer` | sonnet | Read, Glob, Grep, Write, Edit, Bash | `/ndv-audit-fix` | WRITE |
| `onboarder` | sonnet | Read, Grep, Glob, Bash | `/ndv-onboard` — nhiệm vụ SURVEY (Option 1) và DISCOVER (Option 2) | READ-ONLY |

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

## Artifact ownership & gates

| Artifact | Owner tạo/update | Gate trước bước sau |
|---|---|---|
| `<tddRoot>/<Feature>/tdd.md` | `/ndv-gdd-to-tdd` | user review TDD |
| `<matrixRoot>/` (`modules.json` + `index.html`) | `/ndv-module-matrix` — field `status` là giá trị DERIVE theo §Status lifecycle của skill (implemented → planned → specced → proposed); skill khác refresh bằng `/ndv-module-matrix <MODULE>` | layer assignment không cycle |
| `<specsRoot>/<MODULE>/requirement.md` | `/ndv-tdd-to-spec` | — |
| `<specsRoot>/<MODULE>/specify.md` | `/ndv-specify` | zero `NEEDS CLARIFICATION` còn sót |
| `<specsRoot>/<MODULE>/plan.md` | `/ndv-plan` | **user approve** (AskUserQuestion) |
| `<specsRoot>/<MODULE>/tasks.md` | `/ndv-tasks` | **user approve** (AskUserQuestion) |
| code | `/ndv-implement` | build/compile sạch + audit pass |
| `<auditReportRoot>/<MODULE>-<date>.md` | `/ndv-audit-module` | — |
| `<auditReportRoot>/code/<run>/` | `/ndv-audit-code` (READ-ONLY, estate-wide) | — |
| `<auditReportRoot>/standards/<run>/` | `/ndv-audit-standards` (READ-ONLY, UI estate) | — |
| code fixes + tick/Triage trong audit report | `/ndv-audit-fix` | compile sạch theo `verifyNote` + Evidence formula hết hit |
| `<auditReportRoot>/onboard-<date>.md` + matrix/TDD/requirement as-built | `/ndv-onboard` | reverse-doc: clarifications chờ owner trước khi vào forward flow |
| `<auditReportRoot>/audit-learning.md` | `/ndv-audit-code` + `/ndv-audit-standards` (append-only, entry `L-NN`: pattern · root cause · rule-for-next-run · evidence; đọc đầu mỗi run nếu có) | — |

Lưu ý collision: nếu project host đã có spec flow khác đang own artifact cùng tên trong
`<specsRoot>/<MODULE>/` (vd `plan.md`, `tasks.md`), coi artifact đó là LEGACY INPUT
(đọc để không mâu thuẫn) và hỏi user chọn flow trước khi ghi đè.
