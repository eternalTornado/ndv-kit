# ndvkit — GDD → Module Blueprint → Spec (EARS) + ModuleMatrix → Plan → Implement pipeline

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
  │  /ndv-plan     ─▶ plan.md                (technical design, GATE: user approve)
  │  /ndv-tasks    ─▶ tasks.md               (ordered tasks, GATE: user approve)
  │  /ndv-implement           [agent: module-implementer]  (chỉ chạy sau khi plan+tasks approved)
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
- **Một agent, hai vai**: `module-architect` Mode blueprint-review và `code-auditor` VERIFIER là
  instance MỚI của cùng agent (độc lập với author/finder) — ngoại lệ có chủ đích của "resume, không
  respawn".
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
│   ├── code-auditor.md        # FINDER/VERIFIER worker cho /ndv-audit-code (roles, không phải hai agent)
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
| `/ndv-plan` | `<module-id>` | — (inline) | `<specsRoot>/<NNN>_<MODULE>/plan.md` | user approve (AskUserQuestion) |
| `/ndv-tasks` | `<module-id>` | — (inline) | `<specsRoot>/<NNN>_<MODULE>/tasks.md` | user approve (AskUserQuestion); Prerequisites derive từ specify |
| `/ndv-implement` | `<module-id> [--phase <n>] [--continue]` | `module-implementer` | code dưới `<codeRoots>/<Module>/` | hard gate: plan + tasks approved; Prerequisites thỏa; write scope = `paths` của module (scope check sau mỗi phase); cite sweep khi close |
| `/ndv-audit-code` | `[module <module-id>... \| module --all \| current [<path>] \| changes vs-<base>]` | `code-auditor` (vai FINDER + vai VERIFIER) | mode `module` → `<auditReportRoot>/<MODULE>-<yyyy-mm-dd>.md`; mode `current`/`changes` → `<auditReportRoot>/code/<YYYYMMDD-HHMM>-<mode>.md` | READ-ONLY; mode `module` refresh `status` bằng script sau mọi verdict |
| `/ndv-audit-fix` | `[<report-path> \| latest [code \| module <module-id>]] [--ids F-001,F-002] [--severity <min>]` | `audit-fixer` | code fixes + tick/`## Triage` trong report | never commit; triage code-fix / spec-fix → `/ndv-specify --from-audit` / register-fix → `/ndv-module-matrix` / defer; severity filter theo taxonomy đóng R7 |
| `/ndv-onboard` | `[status \| matrix \| reverse-doc [<module-id>...]] (omit = hỏi)` | — (inline; `status` = script only; `matrix` → `module-architect` Mode brownfield; `reverse-doc` → `spec-writer` Mode as-built) | `onboard-<date>.md` / `modules.json` + `modules.md` / requirement as-built | reverse-doc: clarifications chờ owner |
| `/ndv-sync` | `[gdd\|matrix\|spec\|code <target>] [--check-only] [--reanchor]` | — (inline, route tới skill khác) | impact table (không tự tạo artifact riêng) | gate downstream không bị bypass; cite-only edit không void approval |

## Agents

`code-auditor` được skill của nó spawn hai lần với vai khác nhau trong cùng một run: FINDER (quét,
emit candidate) rồi VERIFIER (instance độc lập, cố refute candidate) — hai vai của MỘT agent, không
phải hai agent. Cột Model: frontmatter (default) → routing per dispatch theo
[Model routing](#model-routing).

| Agent | Model | Tools | Dùng bởi | Quyền trên code |
|---|---|---|---|---|
| `spec-writer` | `opus` → sonnet cho back-propagation, cite-only | Read, Glob, Grep, Write, Edit | `/ndv-blueprint-to-spec` (workflow: Mode forward / fix / back-propagation / compose-specify); `/ndv-onboard` (`reverse-doc`, Mode as-built); `/ndv-specify` (contract back-propagation); `/ndv-sync` (cite-only) | READ-ONLY (ghi requirement.md + specify.md, không ghi code) |
| `module-architect` | `opus` → fable cho blueprint-review; sonnet cho register, `<module-id>`, `--verify` fallback | Read, Glob, Grep, Write, Edit, Bash | `/ndv-blueprint` (Mode blueprint, Mode blueprint-review read-only); `/ndv-blueprint-to-spec` (workflow: Mode mapping read-only, Mode register); `/ndv-module-matrix`; `/ndv-onboard` (`matrix`, Mode brownfield) | READ-ONLY (ghi `blueprint.json`, `modules.json`) |
| `module-implementer` | `sonnet` → opus MỘT lần sau vòng compile-fix fail thứ 2 của một phase | Read, Glob, Grep, Write, Edit, Bash | `/ndv-implement` | WRITE |
| `code-auditor` | `fable` → sonnet cho FINDER chỉ có lens `naming` và/hoặc `ui` | Read, Grep, Glob, Bash | `/ndv-audit-code` — vai FINDER và vai VERIFIER | READ-ONLY |
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
| `code-auditor` | `fable` | VERIFIER: fable · FINDER: fable, trừ FINDER chỉ có lens `naming` và/hoặc `ui` → sonnet |
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
