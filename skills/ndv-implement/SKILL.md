---
name: ndv-implement
description: "Bước 4d pipeline ndvkit (SDD implement): thực thi tasks.md đã approve cho một module, phase-by-phase qua agent module-implementer, verify build/compile theo cơ chế của project host, dừng ở gate giữa các phase. Dùng sau khi plan + tasks đều approved."
argument-hint: "<module-id> [--phase <n>] [--continue]"
user-invocable: true
allowed-tools: Read, Glob, Grep, Write, Edit, Bash, Task, Skill, AskUserQuestion, TodoWrite
---

When this skill is invoked:

## Phase 0 — Preconditions (hard gate)

1. Read `.claude/ndvkit/ndvkit.config.json` (`specsRoot`, `matrixRoot`, `verifyNote`). Coding
   rules + precedence do agent `module-implementer` tự resolve (host `.claude/rules/**` > kit
   `.claude/ndvkit/rules/**`).
2. `<specsRoot>/<MODULE>/plan.md` AND `tasks.md` both have `approved: true` —
   else STOP and point at the missing gate. Never implement from an
   unapproved artifact. (Gate này chỉ check ở đây — agent không check lại.)
3. Prerequisites check — tasks.md §Prerequisites (section absent → use the specify.md §Contract
   surface rows). Read `<matrixRoot>/modules.json` for every module's `paths` (fallback `[path]`).
   Per row:
   - `Owner FR` empty or `contract-gap` → NOT satisfied: the need has no owner. Route:
     `/ndv-specify <MODULE>` Phase 4.
   - otherwise satisfied when the `Verify` symbol grep-matches under the owning module's `paths`,
     OR the owner's tasks.md has every task covering that `Owner FR` checked `[x]`.
   - `Stopgap` = `approved …` → satisfied-by-stopgap; the files it names join this run's write scope.
   Any unsatisfied row → do not spawn. AskUserQuestion: (a) run the owning module's pipeline first
   — list the skills to run, this skill does not invoke them; (b) run only the tasks no unsatisfied
   row blocks; (c) approve a stopgap — the user names the files under the owner's `paths` this run
   may write; record `approved <yyyy-mm-dd>: <files>` in the row's `Stopgap` cell. A stopgap leaves
   the `contract-gap` open for `/ndv-sync`.
4. Xác định cơ chế verify build/compile của project (`verifyNote` config;
   nếu rỗng, hỏi user một lần và đề nghị điền vào config). Nếu cơ chế cần
   service/tool đang không chạy (vd editor bridge, build server), request
   user chuẩn bị trước khi tiếp tục.
5. `--continue` resumes from the first unchecked task; `--phase <n>` runs one
   phase only; default runs phases sequentially with a gate between each.

## Phase 1 — Execute per phase

MỘT instance `module-implementer` cho cả run: spawn ở phase đầu, các lần sau RESUME đúng
instance đó (rules + plan + specify đã nằm trong context của nó). Spawn instance mới chỉ khi
harness không resume được, hoặc agent báo context gần đầy — khi đó prompt mới ghi rõ phase
nào đã xong.

For each phase in tasks.md:

1. Snapshot `git status --porcelain` (baseline). Spawn / resume `module-implementer` (Task
   tool) với: module id, phase cần chạy, paths tới plan.md + specify.md + tasks.md, write scope
   (module `paths` + `<specsRoot>/<MODULE>/tasks.md` + files tasks name under no module's
   `paths` + stopgap-approved files). Hành vi (no scope expansion, test policy, no commit) là
   contract của agent — không restate trong prompt.
2. On agent return:
   - **blocked with question** → AskUserQuestion, then resume the same instance with the answer.
   - **blocked: prerequisite <owner> <what>** → the same three options as Phase 0 step 3.
   - **spec-drift finding** → present Finding/Evidence/Impact to the user;
     route: minor → fix spec inline (sync specify.md/plan.md, A→B replace);
     major → stop, send back to `/ndv-specify`/`/ndv-plan`.
   - **completed** → verify: tasks checked in tasks.md, files exist, then
     build/compile check theo cơ chế verify của project (lỗi mới = phase
     chưa done — resume the same instance with the errors).

     Scope check: `git status --porcelain` minus the baseline — every changed/new path must be
     inside the write scope (platform sidecar files, vd `.meta`, follow their asset). A path
     under another module's `paths` = phase NOT done: feed it back to the agent to revert, or
     AskUserQuestion for a stopgap (Phase 0 step 3c). Host without git → run the same check on
     the agent's returned file list.
3. Gate between phases: report files changed + deviations; continue unless
   the user intervened or a gate in tasks.md says stop for review.

## Phase 2 — Registration/manual steps

If the host module convention requires registration artifacts (config asset,
DI wiring, manifest entry…), perform them theo đúng cơ chế host quy định
(generator/menu/tool — không hand-author artifact mà host rules cấm
hand-author).

## Phase 3 — Close

1. All tasks `[x]` → close the register:
   - `python3 .claude/ndvkit/skills/ndv-sync/scripts/ndv_check.py --checks deps` (Windows:
     `python` / `py -3`). Entry của module có `plannedDeps` khác rỗng, hoặc script báo
     `dep-undeclared` / `dep-declared-not-in-code` cho module → invoke skill
     `/ndv-module-matrix <MODULE>` (Skill tool): promote planned edge thành `deps` kèm
     `depEvidence`. Không có gì để promote → KHÔNG spawn `module-architect`. Stack script không
     hỗ trợ / không có Python → luôn invoke skill đó.
   - `… ndv_check.py --refresh-status <MODULE> --write` — `status` re-derive theo
     `/ndv-module-matrix` §Status lifecycle + sinh lại `modules.md` (skill trên đã chạy thì
     bước này đã nằm trong nó).
   Bỏ qua bước này để lại `register-lag` `medium` cho `/ndv-audit-code` tìm thấy.
2. Cite sweep: run
   `python3 .claude/ndvkit/skills/ndv-sync/scripts/ndv_check.py --checks code-cite --touched <files changed this run>`
   (no Python on the host → Grep `<tddRoot>`/`<specsRoot>` for the changed file names and verify
   each cite per `/ndv-sync` Phase 1). Report every `broken-cite` with its owning artifact and
   the route from `/ndv-sync` Phase 2. Fixing them is a cite-only edit (`/ndv-sync` §Cite-only
   edit) — never bundled silently into this run.
3. Report: phases done, files written, deviations, verify result, cite sweep result.
4. Next step: `/ndv-audit-code module <MODULE>`. Không commit trừ khi user yêu cầu.
