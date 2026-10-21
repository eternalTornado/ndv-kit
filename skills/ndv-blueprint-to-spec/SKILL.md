---
name: ndv-blueprint-to-spec
description: "Bước 1 pipeline ndvkit: module blueprint đã approve (/ndv-blueprint) + GDD → modules.json + per-module requirement.md (EARS) + specify.md (clarified) trong spec folder đánh số <NNN>_<MODULE> theo thứ tự implement (kiểu migration), chạy theo step: hỏi phạm vi layer (một/nhiều layer hoặc toàn bộ) → analyze một lần cho cả phạm vi → author + specify LẦN LƯỢT từng layer (Foundation → Layer 1..n, owner trước consumer) bằng workflow multi-agent (Workflow tool), hỏi user giữa các stage (module mapping, GDD gap, EARS ambiguity, contract-gap) và giữa các layer. Idempotent: GDD đổi = --update. Dùng khi blueprint vừa approve hoặc GDD đổi."
argument-hint: "<blueprint-path> [<gdd-path-or-feature-name>] [--update]"
user-invocable: true
allowed-tools: Read, Glob, Grep, Bash, Write, Edit, Workflow, Task, AskUserQuestion, TodoWrite
---

When this skill is invoked:

Gọi skill này = user opt-in multi-agent orchestration (Workflow tool) cho cả run. Script
`workflow.js` cạnh file này: MỘT script, gọi theo `args.stage` (`analyze` một lần cho cả phạm vi;
`author` → `specify` một lần per layer). Agent trong workflow không hỏi user — main session hỏi ở
Gate A / Gate B / checkpoint layer giữa các stage. Protocol: `spec-writer` (Mode forward / fix /
back-propagation / compose-specify) và `module-architect` (Mode mapping / register) sống trong file
agent; vai nội bộ (analyst, quoteVerifier, critic, verifier, reconciler, ambiguity) sống trong
prompt của `workflow.js`; model per role = hằng `MODEL` đầu script (README §Model routing). Skill
không restate các protocol đó.

TodoWrite một todo per step (Step 4 một todo per layer trong phạm vi) để user thấy tiến độ.

## Step 0 — Config & preflight

1. Read `.claude/ndvkit/ndvkit.config.json` → `config` = {`gddRoot`, `specsRoot`, `matrixRoot`,
   `codeRoots`, `contractsDoc`, `rulesRoot`, `kitRulesRoot`, `templates`} (key optional vắng →
   `contractsDoc: ""`, `rulesRoot: ".claude/rules"`, `kitRulesRoot: ".claude/ndvkit/rules"`). Skill
   chạy inline nên tự áp rules: host `.claude/rules/**` + `CLAUDE.md` ưu tiên; host im lặng → kit
   `.claude/ndvkit/rules/**`.
2. `.claude/agents/spec-writer.md` và `.claude/agents/module-architect.md` phải tồn tại (workflow
   resolve `agentType` từ đó) — else STOP, chỉ README §Activation.
3. `scriptPath` = path ABSOLUTE `<repo root>/.claude/ndvkit/skills/ndv-blueprint-to-spec/workflow.js`;
   `date` = hôm nay `yyyy-mm-dd` (script không đọc được đồng hồ). Host override model (prefix
   `[model]` của user, rule model trong `CLAUDE.md` — kể cả `~/.claude/CLAUDE.md`) → `models:
   {<role>: <model>}` theo role của `MODEL`; không có → bỏ field. Rule ép một model cho mọi
   sub-agent cũng là override — routing của kit khi đó không có hiệu lực (README §Model routing).
4. Workflow tool không khả dụng → fallback: chạy đúng các stage/phase theo thứ tự bằng Task tool,
   đọc `workflow.js` lấy prompt + schema + check deterministic làm protocol (`subagent_type` =
   `AGENT_TYPE[role]`, role khác → `general-purpose`; `model` = `models[role]` của bước 3 nếu có,
   không thì `MODEL[role]`); ghi rõ trong report. Workflow bị dừng giữa chừng → relaunch cùng
   `scriptPath` + args với `resumeFromRunId`.

## Parse arguments

- `<blueprint-path>` → `blueprint` (path repo-root-relative): file `.json` → dùng trực tiếp; folder
  chứa `blueprint.json` → file đó; folder không có `blueprint.json` (vd folder report HTML của
  blueprint) → `<matrixRoot>/blueprint.json`, báo user report chỉ là view. Không argument →
  `<matrixRoot>/blueprint.json`. File không tồn tại → STOP, route `/ndv-blueprint` — skill không
  chạy khi thiếu blueprint (phạm vi layer lấy từ blueprint).
- `[<gdd-path-or-feature-name>]` — thu hẹp GDD của run: path dưới `<gddRoot>/**` (file, hoặc folder
  → `**/*.md` bỏ folder bắt đầu bằng `_`) hoặc tên feature → Glob. Nhiều match → AskUserQuestion.
  Không argument → `gddFiles` = `gddSources` của blueprint. File không tồn tại → fail rõ ràng,
  không bịa GDD.
- `--update`, hoặc tự nhận khi đã có requirement.md list các GDD file này trong `gdd-sources`
  hoặc requirement.md legacy có `tdd-source` trỏ TDD cite các file này → `mode: "update"`; còn
  lại `"create"` (module extend có requirement.md sẵn vẫn theo luật Update của spec-writer).
- `feature` = PascalCase từ tên file/folder GDD argument (scheme feature-id/glossary của host thắng);
  không có GDD argument → từ `project` của blueprint; folder tên version (vd `v0.1`) → hỏi tên
  feature.

## Step 1 — Blueprint gate

1. `python3 .claude/ndvkit/skills/ndv-blueprint/scripts/ndv_blueprint.py --blueprint <blueprint>
   --check --json` (Windows: `python` / `py -3`) → `modules` {id: {band, layer}}. Exit 1, hoặc
   blueprint `approved: false` → báo finding blocking, STOP: route `/ndv-blueprint` (approve /
   `--update`). Không có Python → đọc blueprint, tự tính layer theo `deps` (band `foundation` xếp
   row theo dep trong band, band `game` bắt đầu Layer 1) và ghi rõ trong report.
2. GDD argument có file không nằm trong `gddSources` của blueprint → báo, hỏi: chạy `/ndv-blueprint
   --update` trước / tiếp tục.
3. `layers` = danh sách có thứ tự: các row Foundation (`Foundation · row 1..k`, hoặc `Foundation`)
   → `Layer 1..n`; mỗi entry `{label, modules[]}`, `modules` sort theo id (= thứ tự cấp số folder
   trong layer). Per module ghi trạng thái spec: `<specsRoot>/<NNN>_<id>/requirement.md` /
   `specify.md` có hay chưa.
4. `specDirs` = `dirs` của `python3 .claude/ndvkit/skills/ndv-sync/scripts/ndv_check.py --spec-seq
   --json` (map id → folder `<specsRoot>/<NNN>_<id>`, `NNN` = thứ tự implement, README §Quy ước
   chung). Finding `unnumbered` (folder của kit bản cũ) → hỏi: đánh số ngay theo `layers` (`…
   --spec-seq <id có folder không số, theo thứ tự layers> --write`: rename + rewrite reference, rồi
   đọc lại `dirs`; folder của id ngoài blueprint → user archive / xóa) / dừng. `seq-duplicate` /
   `id-duplicate` → blocking, STOP: user gộp / đổi tên folder.

## Step 2 — Scope gate (LUÔN hỏi, kể cả khi đã có spec)

1. In bảng layer → module → trạng thái spec (Step 1.3), rồi AskUserQuestion "Viết spec cho phạm
   vi nào?" với options:
   - `Toàn bộ layer` — mọi layer, lần lượt Foundation → Layer n.
   - `Layer kế tiếp: <label>` — layer thấp nhất còn module chưa có requirement.md (update mode:
     layer thấp nhất có module bị drift); không có → bỏ option này.
   - `Foundation` — mọi row Foundation (bỏ option khi đã trùng option trên).
   - Other (tự nhập): danh sách layer / khoảng, vd `F, L1-L3`, `L4`, hoặc module id.
2. `scope` = các layer đã chọn theo thứ tự của `layers`; module id lẻ → chỉ module đó trong layer
   của nó. `moduleFilter` = mọi module của `scope`.
3. Owner chưa sẵn: module trong `scope` có dep (`deps` blueprint, `from` = module đó) tới module
   ngoài `scope` chưa có requirement.md → liệt kê, hỏi: thêm layer của owner vào scope / tiếp tục
   (contract tới owner đó sẽ thành `contract-gap` ở Gate B; owner cấp số sau consumer → `seq-order`).

## Step 3 — Scout (inline, rẻ)

1. Per GDD file: Grep `^#{1,3} ` (kèm số dòng) + đếm dòng → `chunks: [{id, file, headings}]` —
   một chunk per nhóm section top-level, ≤~400 dòng per chunk, `id` = `c1`, `c2`, …. KHÔNG đọc body
   GDD (analyst đọc). File không có heading `^#{1,3} ` nào → fail rõ cho file đó (anchor không cite
   được): báo Design thêm heading rồi re-run — không gửi chunk `headings: []`, không bỏ file im lặng.
2. Update mode: `existingRequirements` = mọi `<specsRoot>/<NNN>_<id>/requirement.md` của module trong
   `scope` có `gdd-sources` chứa các file này (Grep frontmatter) + requirement.md legacy có
   `tdd-source` trỏ TDD cite các file này.
3. Update mode — anchor đã mất: `python3 .claude/ndvkit/skills/ndv-sync/scripts/ndv_check.py
   --checks doc-cite --artifact <existingRequirements> --json` → mỗi finding `doc-missing` /
   `section-not-found` có cite vào một GDD file của run → `removedAnchors[]`
   `{module, fr, cite, change: "removed"}` (`module` = id của folder requirement.md, bỏ prefix
   `NNN_`; `fr` = heading `### <ID>` gần nhất phía trên dòng finding). Không có Python → Grep từng heading được cite.

## Step 4 — Stage `analyze` (một lần cho cả scope)

`Workflow({scriptPath, args: {stage: "analyze", feature, mode, date, gddFiles, config, blueprint,
specDirs, moduleFilter, models?, chunks, existingRequirements}})` → chờ notification hoàn tất, đọc
result
(`items`, `gaps`, `mapping`, `uncovered`, `outOfFilter`, `changed`, `coverageChecked`, `models`,
`log`). `mapping: null` (mapper fail) → spawn `module-architect` (Task, `model: opus`) Mode mapping
với `items` + `moduleFilter` + path `blueprint` trước Gate A.

## Gate A — module mapping + GDD gap (AskUserQuestion, batch ≤4 per call)

1. Bảng mapping, nhóm theo layer của `scope`: module → band + layer → new / extend (`extends`) →
   `gddSections` → responsibilities (key · summary). Hỏi approve / adjust, kèm mọi câu
   `alternatives[]`; mỗi key `unmapped` → gán module hoặc `Out of scope`. `outOfFilter` {key, owner}
   chỉ báo ở đây (thuộc layer ngoài scope — viết khi chạy layer đó); `uncovered` quay lại ở Gate B.
   `coverageChecked: false` (critic không chạy) → hỏi: chạy lại stage analyze, hay chấp nhận
   coverage chưa kiểm. Key `unmapped` reason `blueprint-miss` → hỏi: gán vào module blueprint X /
   `Out of scope` / dừng để `/ndv-blueprint --update` (thêm module) rồi re-run. Module trong scope
   không nhận key nào → liệt kê (bình thường khi GDD của run không chạm concern đó); muốn có
   requirement.md cho module đó → gán ≥1 key cho nó (stage author không nhận `responsibilities: []`
   ở mode create). Module id trong mapping không có trong blueprint → hỏi: đổi sang module
   blueprint / dừng để `/ndv-blueprint --update`.
2. Mỗi `gaps[]`: ≤3 option có cite của analyst + "Defer" (gap 0 option → tự viết ≥1 option có cite
   trước khi hỏi). Answer → `decisions[]` `{gapId, cite, question, answer, date}` (answer literal).
   Defer → `deferred[]` — gap giữ `NEEDS CLARIFICATION` trong requirement.md, module đó không có
   specify.md run này. Answer mâu thuẫn literal của GDD → KHÔNG ghi decision (R3): báo Design sửa
   GDD rồi re-run `--update`; gap đó đi `deferred[]`. Decision đã chốt của blueprint (có `cite` vào
   GDD) mà settle một câu hỏi cấp requirement → `decisions[]` `{gapId: "BP-<id>", cite, question,
   answer, date}` (`answer` / `date` = phần literal trong ngoặc kép và ngày của field `answer`
   blueprint `decision: <date> — "<answer>"`) — không hỏi lại. Việc approve cả blueprint KHÔNG phải
   nguồn `decision:` (R5).
3. Gắn `modules: [<id>]` cho MỌI entry `decisions[]` / `deferred[]` theo mapping đã confirm: module
   có responsibility cite đúng anchor đó; không có → mọi module có responsibility cite cùng GDD
   file. Step 5 dùng field này để chia entry về đúng layer.
4. Update mode: mỗi FR trong `removedAnchors` (và `changed` có `change: "removed"`) → hỏi: xóa FR,
   hay giữ với `decision:` (answer ghi vào field `decision` của chính entry đó). Module có drift mà
   không còn responsibility nào vẫn vào author với `responsibilities: []` (entry `{id, name, isNew:
   false, gddSections: []}` lấy từ modules.json) — liệt kê trong bảng mapping ở bước 1.
5. `items` rỗng, hoặc sau confirm không còn module nào (kể cả drift-only) → KHÔNG chạy Step 5:
   report `uncovered` + `gaps` + `outOfFilter` + mọi dòng `log`, rồi dừng.

## Step 5 — Per layer: author → Gate B → specify (lặp theo thứ tự `scope`)

`layerModules` = module của mapping đã confirm thuộc layer này (kể cả drift-only); rỗng → bỏ qua
layer, ghi report. Layer thấp viết trước nên khi tới consumer, requirement.md của owner đã có.

### 5a — Folder + baseline

Folder: module của `layerModules` chưa có trong `specDirs` → `python3
.claude/ndvkit/skills/ndv-sync/scripts/ndv_check.py --spec-seq <các id đó, theo thứ tự của layer>
--write --json`; `specDirs` = `dirs` của output. Số cấp TRƯỚC stage author nên batch song song
không tranh số; module fail ở author giữ folder rỗng — số đã cấp, run sau dùng lại.

Baseline: kit không commit nên git không phải "trước run": `baselineDir` = thư mục tạm ABSOLUTE
(macOS/Linux `mktemp -d`; Windows `New-Item -ItemType Directory "$env:TEMP\ndv-<date>-<n>"`), tạo
MỘT lần cho cả run; copy `requirement.md` + `specify.md` ĐANG CÓ của `layerModules` sang
`<baselineDir>/<MODULE>/` trước stage author của layer. File chưa có → không copy (= absent).

### 5b — Stage `author`

Args: common (`feature, mode, date, gddFiles, config, blueprint, specDirs, models?`) +
`baselineDir` + `modules` = mapping của `layerModules` (responsibilities mở rộng thành `{key, kind, summary, cite}`
từ `items`) + `decisions` / `deferred` có `modules` giao `layerModules` + `changed` (update mode:
entry của `changed` analyze ∪ `removedAnchors` mà module hoặc prefix FR id thuộc `layerModules`,
kèm `decision` khi user giữ FR). Sau khi xong:

1. `matrix: null` (register fail) → spawn `module-architect` (Task, `model: sonnet`) Mode register
   với mapping của layer + các requirement.md đã ghi; output của agent thay `matrix`.
   `contractGaps: null` (reconciler fail) → `python3
   .claude/ndvkit/skills/ndv-sync/scripts/ndv_check.py --checks contract-gap --artifact <các
   requirement.md đã ghi> --json`; mỗi finding status `contract-gap` (bỏ `contract-stopgap`) → mở
   `artifact:line`, `row` = cell đầu verbatim; bảng Contract surface → `kind: surface`, consumer =
   module của folder artifact (id, bỏ `NNN_`), owner = cell `Owning module`; bảng Consumer
   obligations → `kind: obligation`, owner = module của folder artifact, consumer = cell `Consumer
   module`.
2. `python3 .claude/ndvkit/skills/ndv-blueprint/scripts/ndv_blueprint.py --blueprint <blueprint>
   --check` sau register — `matrix-band-violation` (Contract surface làm module Foundation depend
   module game) → hỏi ở Gate B: sửa row (withdraw / đổi owner) / `/ndv-blueprint --update` đổi band.
3. `… ndv_check.py --refresh-status <matrix.touched> --write` (exit 2 → report; không có Python →
   `/ndv-module-matrix` §Status lifecycle fallback).

### 5c — Gate B: ambiguity + contract-gap (AskUserQuestion, batch ≤4 per call)

1. `ambiguities[].questions` (options có cite) + `modules[].open` mới lộ ra khi viết (không phải
   gap đã Defer ở Gate A) → `answers[]` `{module, ref, question, answer, kind: "clarify"}` (`ref` =
   FR id mà answer settle — `fr` của question / `ref` của open).
2. Mỗi `contractGaps[]` row: (a) add FR vào target, (b) stopgap có chủ đích, (c) withdraw need —
   semantics của `/ndv-specify` Phase 4 (target = owning module cho Contract surface row, consumer
   cho Consumer obligations row) → `gapChoices[]` `{consumer, row, owner, kind, choice: "add" |
   "stopgap" | "withdraw"}`. Owner ở layer đã viết ở step trước vẫn là target hợp lệ (stage specify
   back-propagate); owner ngoài scope chưa có requirement.md → chỉ stopgap / withdraw.
3. Layer đầu tiên của scope: `uncovered` của analyze; mọi layer: `unresolvedDefects` của author.
   Hỏi add / `Out of scope` của module X / fix → `answers[]` entry của module đó với `kind: "add" |
   "out-of-scope" | "fix"` (`ref` = GDD cite / responsibility key / defect id; out-of-scope: answer
   nêu module nhận). Answer cho module thuộc layer sau → giữ lại, truyền ở stage specify của layer
   đó. Áp theo `spec-writer` §Mode compose-specify bước 1: nội dung GDD giữ Source literal GDD; chỉ
   lựa chọn của user nơi GDD im lặng mới thành `+ decision:`.
4. `matrix.cycles` = blocking: module trong cycle không vào 5d; report Finding/Evidence/Impact
   + `findings` của architect. Module `failed: true` cũng không vào 5d.

### 5d — Stage `specify`

Args: common + `baselineDir` + `modules: [{id, path}]` (`layerModules` trừ cycle / failed) +
`answers` của các module đó + `gapChoices` của layer. Sau đó:

1. Có `withdraw` của row `kind: surface` đã áp (row Contract surface bị xóa SAU register) → spawn
   `module-architect` (Task, `model: sonnet`) Mode register cho các consumer đó (mapping rỗng,
   requirement.md hiện tại) — re-derive `plannedDeps` từ row còn lại.
2. Refresh-status lại như 5b bước 3.

### 5e — Checkpoint layer

Còn layer trong scope → tóm tắt layer vừa xong (module · FR/NFR count · specify.md ghi chưa ·
contract-gap mở) rồi AskUserQuestion: tiếp `<layer kế>` / dừng tại đây (Step 6 report phần đã
xong; layer còn lại chạy sau bằng cùng `<blueprint-path>` và chọn scope đó).

## Step 6 — Report

- Scope đã chọn, layer đã chạy / bỏ qua / dừng trước.
- Per module (nhóm theo layer, kèm folder `<NNN>_<id>`): FR/NFR count; specify.md đã ghi hay chưa
  (+ `open` còn lại → `/ndv-specify <MODULE>`); `decision:` cite đã thêm; contract-gap đóng / còn mở;
  `orphanContractFRs`, `removed`, `contractsDocProposals` (addition đề xuất cho registry
  `contractsDoc` — user tự áp), `conflicts`, `unresolvedDefects`.
- `followUps` của stage specify (`/ndv-specify <Target>` cho target ngoài layer có requirement.md
  đổi; conflict với `Out of scope`); matrix layer table + cycles; `uncovered` / `outOfFilter`.
- `… ndv_check.py --spec-seq` sau run: finding `seq-order` (owner cấp số sau consumer) → nêu
  thứ tự implement thật (owner trước); số không đổi (kiểu migration).
- Model dùng per stage (`models` của từng result) + mọi dòng `log` báo fail / drop / giới hạn.
- Update mode: FR đổi text — `changed[].fr` (analyze) ∪ `removed` (author) ∪ `changedIds`
  (specify); module = prefix của FR id — mà `plan.md` có `approved: true` → `/ndv-plan <MODULE>`
  (re-approve).
- Next: `/ndv-plan <MODULE>`. Không commit. `baselineDir` là thư mục tạm — xóa sau report.

## Legacy host (requirement.md còn cite TDD)

`tdd-source` / Source trỏ path TDD → stage author re-cite sang GDD anchor mà TDD đó quote
(`spec-writer` §Mode forward); câu TDD mang `decision:` → giữ decision (kèm GDD anchor của
section), không hỏi lại; không có GDD cite lẫn decision → `NEEDS CLARIFICATION`. requirement.md
`origin: reverse-engineered` còn cite TDD (as-built cũ) → `/ndv-onboard reverse-doc <MODULE>`. Mọi
module của feature đã re-cite → report nhắc user có thể archive folder TDD — skill không bao giờ tự
xóa.
