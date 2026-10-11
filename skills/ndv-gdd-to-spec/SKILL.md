---
name: ndv-gdd-to-spec
description: "Bước 1 pipeline ndvkit: GDD → modules.json + per-module requirement.md (EARS) + specify.md (clarified) bằng MỘT workflow multi-agent (Workflow tool, 3 stage analyze → author → specify), hỏi user giữa các stage (module mapping, GDD gap, EARS ambiguity, contract-gap). Idempotent: GDD đổi = --update. Dùng khi có GDD mới/đổi."
argument-hint: "<gdd-path-or-feature-name> [<module-id>...] [--update]"
user-invocable: true
allowed-tools: Read, Glob, Grep, Bash, Write, Edit, Workflow, Task, AskUserQuestion, TodoWrite
---

When this skill is invoked:

Gọi skill này = user opt-in multi-agent orchestration (Workflow tool) cho cả run. Script
`workflow.js` cạnh file này: MỘT script, gọi ba lần theo `args.stage` (`analyze` → `author` →
`specify`). Agent trong workflow không hỏi user — main session hỏi ở Gate A / Gate B giữa các
stage. Protocol: `spec-writer` (Mode forward / fix / back-propagation / compose-specify) và
`module-architect` (Mode mapping / register) sống trong file agent; vai nội bộ (analyst,
quoteVerifier, critic, verifier, reconciler, ambiguity) sống trong prompt của `workflow.js`; model
per role = hằng `MODEL` đầu script (README §Model routing). Skill không restate các protocol đó.

## Phase 0 — Config & preflight

1. Read `.claude/ndvkit/ndvkit.config.json` → `config` = {`gddRoot`, `specsRoot`, `matrixRoot`,
   `codeRoots`, `contractsDoc`, `rulesRoot`, `kitRulesRoot`, `templates`} (key optional vắng →
   `contractsDoc: ""`, `rulesRoot: ".claude/rules"`, `kitRulesRoot: ".claude/ndvkit/rules"`). Skill
   chạy inline nên tự áp rules: host `.claude/rules/**` + `CLAUDE.md` ưu tiên; host im lặng → kit
   `.claude/ndvkit/rules/**`.
2. `.claude/agents/spec-writer.md` và `.claude/agents/module-architect.md` phải tồn tại (workflow
   resolve `agentType` từ đó) — else STOP, chỉ README §Activation.
3. `scriptPath` = path ABSOLUTE `<repo root>/.claude/ndvkit/skills/ndv-gdd-to-spec/workflow.js`;
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

- `<gdd-path-or-feature-name>` — path dưới `<gddRoot>/**` hoặc tên feature → Glob. Nhiều match →
  AskUserQuestion; không match / không argument → list GDD file chưa requirement.md nào cite trong
  `gdd-sources` (requirement.md legacy: qua `gdd-sources` của TDD mà `tdd-source` trỏ tới) rồi
  hỏi. `<gddRoot>` hoặc file không tồn tại → fail rõ ràng, không bịa GDD.
- `[<module-id>...]` → `moduleFilter`.
- `--update`, hoặc tự nhận khi đã có requirement.md list các GDD file này trong `gdd-sources`
  hoặc requirement.md legacy có `tdd-source` trỏ TDD cite các file này → `mode: "update"`; còn
  lại `"create"` (module extend có requirement.md sẵn vẫn theo luật Update của spec-writer).
- `feature` = PascalCase từ tên file/folder GDD (scheme feature-id/glossary của host thắng).

## Phase 1 — Scout (inline, rẻ)

1. Per GDD file: Grep `^#{1,3} ` (kèm số dòng) + đếm dòng → `chunks: [{id, file, headings}]` —
   một chunk per nhóm section top-level, ≤~400 dòng per chunk, `id` = `c1`, `c2`, …. KHÔNG đọc body
   GDD (analyst đọc). File không có heading `^#{1,3} ` nào → fail rõ cho file đó (anchor không cite
   được): báo Design thêm heading rồi re-run — không gửi chunk `headings: []`, không bỏ file im lặng.
2. Update mode: `existingRequirements` = mọi `<specsRoot>/*/requirement.md` có `gdd-sources` chứa
   các file này (Grep frontmatter) + requirement.md legacy có `tdd-source` trỏ TDD cite các file này.
3. Update mode — anchor đã mất: `python3 .claude/ndvkit/skills/ndv-sync/scripts/ndv_check.py
   --checks doc-cite --artifact <existingRequirements> --json` (Windows: `python` / `py -3`) → mỗi
   finding `doc-missing` / `section-not-found` có cite vào một GDD file của run → `removedAnchors[]`
   `{module, fr, cite, change: "removed"}` (`module` = folder của requirement.md, `fr` = heading
   `### <ID>` gần nhất phía trên dòng finding). Không có Python → Grep từng heading được cite.

## Phase 2 — Stage `analyze`

`Workflow({scriptPath, args: {stage: "analyze", feature, mode, date, gddFiles, config,
moduleFilter, models?, chunks, existingRequirements}})` → chờ notification hoàn tất, đọc result
(`items`, `gaps`, `mapping`, `uncovered`, `outOfFilter`, `changed`, `coverageChecked`, `models`,
`log`). `mapping: null` (mapper fail) → spawn `module-architect` (Task, `model: opus`) Mode mapping
với `items` + `moduleFilter` trước Gate A.

## Gate A — module mapping + GDD gap (AskUserQuestion, batch ≤4 per call)

1. Bảng mapping: module → new / extend (`extends`) → `gddSections` → responsibilities (key ·
   summary). Hỏi approve / adjust, kèm mọi câu `alternatives[]`; mỗi key `unmapped` → gán module
   hoặc `Out of scope`. `outOfFilter` {key, owner} + `uncovered` chỉ báo ở đây (`uncovered` quay
   lại ở Gate B). `coverageChecked: false` (critic không chạy) → hỏi: chạy lại stage analyze, hay
   chấp nhận coverage chưa kiểm.
2. Mỗi `gaps[]`: ≤3 option có cite của analyst + "Defer" (gap 0 option → tự viết ≥1 option có cite
   trước khi hỏi). Answer → `decisions[]` `{gapId, cite, question, answer, date}` (answer literal).
   Defer → `deferred[]` — gap giữ `NEEDS CLARIFICATION` trong requirement.md, module đó không có
   specify.md run này. Answer mâu thuẫn literal của GDD → KHÔNG ghi decision (R3): báo Design sửa
   GDD rồi re-run `--update`; gap đó đi `deferred[]`.
3. Update mode: mỗi FR trong `removedAnchors` (và `changed` có `change: "removed"`) → hỏi: xóa FR,
   hay giữ với `decision:` (answer ghi vào field `decision` của chính entry đó). Module có drift mà
   không còn responsibility nào vẫn vào author với `responsibilities: []` (entry `{id, name, isNew:
   false, gddSections: []}` lấy từ modules.json) — liệt kê trong bảng mapping ở bước 1.
4. `items` rỗng, hoặc sau confirm không còn module nào (kể cả drift-only) → KHÔNG chạy Phase 3/4:
   report `uncovered` + `gaps` + `outOfFilter` + mọi dòng `log`, rồi dừng.
5. Baseline (kit không commit nên git không phải "trước run"): `baselineDir` = thư mục tạm ABSOLUTE
   (macOS/Linux `mktemp -d`; Windows `New-Item -ItemType Directory "$env:TEMP\ndv-<date>-<n>"`);
   copy `requirement.md` + `specify.md` ĐANG CÓ của mọi module sẽ vào Phase 3 sang
   `<baselineDir>/<MODULE>/`. File chưa có → không copy (= absent).

## Phase 3 — Stage `author`

Args: common + `baselineDir` + `modules` = mapping đã confirm (responsibilities mở rộng thành
`{key, kind, summary, cite}` từ `items`) + `decisions` + `deferred` + `changed` (update mode:
`changed` của analyze ∪ `removedAnchors`, kèm `decision` khi user giữ FR). Sau khi xong:

1. `matrix: null` (register fail) → spawn `module-architect` (Task, `model: sonnet`) Mode register
   với mapping + các requirement.md đã ghi; output của agent thay `matrix`. `contractGaps: null`
   (reconciler fail) → `python3 .claude/ndvkit/skills/ndv-sync/scripts/ndv_check.py --checks
   contract-gap --artifact <các requirement.md đã ghi> --json`; mỗi finding status `contract-gap`
   (bỏ `contract-stopgap`) → mở `artifact:line`, `row` = cell đầu verbatim; bảng Contract surface →
   `kind: surface`, consumer = module folder của artifact, owner = cell `Owning module`; bảng
   Consumer obligations → `kind: obligation`, owner = module folder của artifact, consumer = cell
   `Consumer module`.
2. `… ndv_check.py --refresh-status <matrix.touched> --write` (exit 2 → report; không có Python →
   `/ndv-module-matrix` §Status lifecycle fallback).

## Gate B — ambiguity + contract-gap (AskUserQuestion, batch ≤4 per call)

1. `ambiguities[].questions` (options có cite) + `modules[].open` mới lộ ra khi viết (không phải
   gap đã Defer ở Gate A) → `answers[]` `{module, ref, question, answer, kind: "clarify"}` (`ref` =
   FR id mà answer settle — `fr` của question / `ref` của open).
2. Mỗi `contractGaps[]` row: (a) add FR vào target, (b) stopgap có chủ đích, (c) withdraw need —
   semantics của `/ndv-specify` Phase 4 (target = owning module cho Contract surface row, consumer
   cho Consumer obligations row) → `gapChoices[]` `{consumer, row, owner, kind, choice: "add" |
   "stopgap" | "withdraw"}`.
3. `uncovered` của analyze + `unresolvedDefects` của author: hỏi add / `Out of scope` của module X
   / fix → `answers[]` entry của module đó với `kind: "add" | "out-of-scope" | "fix"` (`ref` = GDD
   cite / responsibility key / defect id; out-of-scope: answer nêu module nhận). Áp theo
   `spec-writer` §Mode compose-specify bước 1: nội dung GDD giữ Source literal GDD; chỉ lựa chọn của
   user nơi GDD im lặng mới thành `+ decision:`.
4. `matrix.cycles` = blocking: module trong cycle không vào Phase 4; report Finding/Evidence/Impact
   + `findings` của architect. Module `failed: true` cũng không vào Phase 4.

## Phase 4 — Stage `specify`

Args: common + `baselineDir` + `modules: [{id, path}]` (trừ cycle / failed) + `answers` +
`gapChoices`. Sau đó:

1. Có `withdraw` của row `kind: surface` đã áp (row Contract surface bị xóa SAU register) → spawn
   `module-architect` (Task, `model: sonnet`) Mode register cho các consumer đó (mapping rỗng,
   requirement.md hiện tại) — re-derive `plannedDeps` từ row còn lại.
2. Refresh-status lại như Phase 3 bước 2.

## Phase 5 — Report

- Per module: FR/NFR count; specify.md đã ghi hay chưa (+ `open` còn lại → `/ndv-specify
  <MODULE>`); `decision:` cite đã thêm; contract-gap đóng / còn mở; `orphanContractFRs`,
  `removed`, `contractsDocProposals` (addition đề xuất cho registry `contractsDoc` — user tự áp),
  `conflicts`, `unresolvedDefects`.
- `followUps` của stage specify (`/ndv-specify <Target>` cho target ngoài run có requirement.md
  đổi; conflict với `Out of scope`); matrix layer table + cycles; `uncovered` / `outOfFilter`.
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
