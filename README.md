# ndvkit — GDD → TDD → ModuleMatrix → Spec (EARS) → Implement pipeline

Bộ agents + skills PORTABLE cho vòng đời feature game project, format theo
[Claude-Code-Game-Studios](https://github.com/Donchitos/Claude-Code-Game-Studios) `.claude/`.
Kit không chứa reference cứng vào một project cụ thể — mọi giá trị per-project nằm ở
`ndvkit.config.json`, mọi convention per-project defer về `.claude/rules/**` của project host.

## Rule precedence (áp cho MỌI agent + skill trong kit)

1. `.claude/rules/**` + `CLAUDE.md` của project host (auto-load) **thắng** mọi thứ trong kit khi mâu thuẫn.
2. Domain nào host KHÔNG define → dùng **kit default rules** tại [`rules/`](rules/README.md) (`kitRulesRoot`) — bộ rules đầy đủ `Shared/` + `Unity/` + `Server/`, project-agnostic. Project mới có thể copy nguyên folder này vào `.claude/rules/` để auto-load (adopt = tự define rules riêng từ đó).
3. Trước khi viết artifact/code, đọc rules liên quan theo thứ tự trên (coding style, naming, architecture, pitfalls, security/authority, id allocation).
4. Kit methodology baseline (inline dưới đây, trùng với `rules/Shared/ai-discipline.md` — áp dụng khi các tầng trên không nói khác):
   - **Verify trước khi claim** — mọi khẳng định về file/API/state phải qua tool (Read/Grep/Glob) trong session.
   - **Không bịa** — source thiếu info → ghi `NEEDS CLARIFICATION: <câu hỏi cụ thể>` inline rồi dừng, không đoán từ "typical game".
   - **Literal quote** — constant/formula/enum/edge-case chuyển từ source sang artifact phải quote nguyên văn kèm cite `<path>#<section>` hoặc `<path>:<line>`.
   - **Finding format** — mọi audit/drift finding gồm Finding / Evidence (cite + quote) / Impact.
   - **Update = replace** — đổi A thành B thì xóa A ghi B, không append changelog vào body.
   - **Không estimate/timeline** trong artifact; **không commit** trừ khi user yêu cầu.

## Pipeline

```text
<gddRoot>/**                                (Design — nguồn duy nhất của gameplay truth)
  │  /ndv-gdd-to-tdd          [agent: tdd-writer]
  ▼
<tddRoot>/<Feature>/tdd.md                  (chỉ technical concern, mọi claim cite GDD anchor)
  │  /ndv-module-matrix       [agent: module-architect]
  ▼
<matrixRoot>/modules.json + index.html      (waterfall layers: L0 Foundation → Ln; HTML+CSS light theme)
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

## Layout

```text
.claude/ndvkit/
├── README.md
├── ndvkit.config.json         # giá trị per-project — file DUY NHẤT cần sửa khi đem sang project khác
├── rules/                     # KIT DEFAULT RULES — Shared/ + Unity/ + Server/ (xem rules/README.md)
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

## Activation

Kit ở trạng thái STAGED trong `.claude/ndvkit/` — Claude Code chỉ auto-discover
`.claude/agents/` và `.claude/skills/`. Khi muốn kích hoạt:

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

## Artifact ownership & gates

| Artifact | Owner tạo/update | Gate trước bước sau |
|---|---|---|
| `<tddRoot>/<Feature>/tdd.md` | `/ndv-gdd-to-tdd` | user review TDD |
| `<matrixRoot>/` | `/ndv-module-matrix` | layer assignment không cycle |
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

Lưu ý collision: nếu project host đã có spec flow khác đang own artifact cùng tên trong
`<specsRoot>/<MODULE>/` (vd `plan.md`, `tasks.md`), coi artifact đó là LEGACY INPUT
(đọc để không mâu thuẫn) và hỏi user chọn flow trước khi ghi đè.
