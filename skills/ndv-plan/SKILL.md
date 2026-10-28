---
name: ndv-plan
description: "Bước 2 pipeline ndvkit (SDD plan): từ specify.md tạo/refresh <specsRoot>/<NNN>_<MODULE>/plan.md — technical design (module skeleton, types, data flow, state & guards, wiring) theo module convention của project host. Plan review độc lập (code-auditor vai PLAN-REVIEWER) trước gate; kết thúc bằng gate AskUserQuestion approve; plan chưa approve thì không được implement. Dùng khi specify mới/đổi hoặc design cần revise."
argument-hint: "<module-id>"
user-invocable: true
allowed-tools: Read, Glob, Grep, Write, Edit, Bash, Task, AskUserQuestion, TodoWrite
---

When this skill is invoked:

## Phase 0 — Config & rules

Read `.claude/ndvkit/ndvkit.config.json` (`specsRoot`, `matrixRoot`,
`templates`). Rule source: host `.claude/rules/**` + `CLAUDE.md` nếu có; domain nào
host không define → dùng kit default rules tại `.claude/ndvkit/rules/**`. Host thắng
khi mâu thuẫn. Spec folder `<specsRoot>/<NNN>_<MODULE>/` = field `spec` của entry modules.json,
chưa có → Glob `<specsRoot>/*_<MODULE>/` (`NNN` = thứ tự implement, README §Quy ước chung).

## Phase 1 — Load context

1. Read `<specsRoot>/<NNN>_<MODULE>/specify.md` (missing or containing
   `NEEDS CLARIFICATION` → fail, point at `/ndv-specify`).
2. Read the `<matrixRoot>/modules.json` entry (layer + allowed deps) and the
   contract surface docs of every dependency.
3. Resolve rule files hai tầng theo `/ndv-audit-code` Step 0 — host tier (toàn bộ `<rulesRoot>/**`
   + `CLAUDE.md`) trước, rồi kit tier per lens (`patterns`, `naming`, security của `spec`; `ui` khi
   module có UI) — và Read hết. Đây là bộ file mà
   plan review (Phase 3) và audit chấm theo; implementer copy literal của plan, nên tên type /
   member / event / enum trong plan phải thoả chúng ngay từ plan.
4. Read existing `plan.md` if present — update mode preserves approved
   decisions unless the specify delta invalidates them (call those out).
5. Read the existing code the plan will extend: Glob the module `path` from the
   modules.json entry and Read every source file the design touches. Every as-built
   reference in plan.md cites `<path>::<Type>.<Member>` of a symbol opened in this
   session (R3) — anchors are never carried over from specify.md, requirement.md, or
   modules.json without re-opening the file, and code is never cited by bare `:<line>`.

## Phase 2 — Design

Fill `<templates>/plan-template.md`:
- **Module skeleton**: folder layout, entry/registration class, namespace —
  ALL per the host module conventions. If the design needs a structure the
  host rules don't allow/declare, flag it as a decision for the user, not a
  silent deviation.
- **Types**: classes/interfaces per folder, suffix/naming per the rule files of Phase 1 step 3.
- **Shared logic**: logic dùng ở ≥2 type (compose / parse / format / validate / checksum) → MỘT
  helper khai báo trong §2, các type kia gọi lại. Tasks chia theo file, nên helper không khai báo
  ở plan sẽ bị viết lại ở từng task.
- **State & guards** (§3a): service giữ mutable state qua nhiều operation hoặc async flow → liệt
  kê state field + transition set / reset, invariant giữa các field, guard matrix operation ×
  precondition mà spec đòi (mỗi ô: guard + AC cite, hoặc `N/A` + lý do). Flow §3 gọi guard /
  transition theo tên, không viết lại điều kiện inline. Stateless → `N/A — stateless` + lý do.
- **Data flow**: how each FR is realized — component interaction, events,
  wire contracts (event/serialization conventions per host rules). Existing
  components/methods are named by symbol `<path>::<Type>.<Member>`; new ones by
  name + folder per the skeleton.
- **As-built vs to-be-replaced**: code the plan keeps or extends is cited by symbol in present
  tense. Code the plan's own tasks will REPLACE is written as `trước implement: …` + the symbol of
  the containing member — never `:<line>`, never "currently"/"hiện tại": that sentence turns false
  the moment `/ndv-implement` lands, and an approved plan must stay true after its own implement.
- **Dependency wiring**: the module's declared dependencies must equal the
  modules.json entry's `deps[] ∪ plannedDeps[]`; anything extra = go back to
  `/ndv-module-matrix` first (an edge the plan needs but code does not have yet
  belongs in `plannedDeps`, with spec evidence).
- **UI (if any)**: per the host UI conventions (framework, authoring rules,
  binding pattern).
- **Risks & pitfalls**: which host pitfalls apply and how the design avoids
  them.
- **FR → design element mapping table** (every FR lands somewhere).

Design decisions the spec does not constrain: pick ONE and justify with a
cite; if genuinely irreversible or user-taste, AskUserQuestion with 2-3
options.

## Phase 3 — Plan review (trước gate)

1. Spawn (Task tool) `subagent_type: code-auditor`, model: fable, vai PLAN-REVIEWER: path plan.md ·
   specify.md · rule files của Phase 1 step 3 · entry modules.json. Agent type chưa đăng ký →
   `general-purpose` (cùng model) + dòng đầu prompt: "Read `.claude/ndvkit/agents/code-auditor.md`
   và làm đúng vai PLAN-REVIEWER trong đó".
2. Per candidate: đồng ý → sửa plan.md (A→B, cite). Không đồng ý → dispute kèm evidence. Plan đúng
   nhưng AC sai → KHÔNG sửa plan; mang sang gate như spec-fix (`/ndv-specify <MODULE>`).
3. Resume đúng instance reviewer MỘT lần với danh sách đã sửa / dispute. Không loop thêm.
4. Còn `still-present`, dispute chưa được chấp nhận, hoặc `NEW` → mang sang gate.

## Phase 4 — Approval gate

1. Present the plan summary (skeleton + FR mapping + risks) + plan review tally (raised / fixed /
   disputed / open) + mọi finding còn mở ≥ `medium` kèm Fix.
2. AskUserQuestion: "Approve plan cho <MODULE>?" — options: Approve / Revise
   (specify what) / Reject.
3. On Approve: set frontmatter `approved: true` + date in plan.md, then refresh status:
   `python3 .claude/ndvkit/skills/ndv-sync/scripts/ndv_check.py --refresh-status <MODULE> --write`
   (`status` re-derive theo `/ndv-module-matrix` §Status lifecycle — module đã có code và hết
   task mở vẫn là `implemented` cho tới khi `/ndv-tasks` thêm task mới).
   On Revise: apply, re-ask. Never mark approved yourself without the answer.
4. Next: `/ndv-tasks <MODULE>`.
