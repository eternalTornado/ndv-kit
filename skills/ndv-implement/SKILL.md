---
name: ndv-implement
description: "Bước 4 pipeline ndvkit (SDD implement): thực thi tasks.md đã approve cho một module, phase-by-phase qua agent module-implementer, verify build/compile theo cơ chế của project host, dừng ở gate giữa các phase. Dùng sau khi plan + tasks đều approved."
argument-hint: "<module-id> [--phase <n>] [--continue]"
user-invocable: true
allowed-tools: Read, Glob, Grep, Write, Edit, Bash, Task, Skill, AskUserQuestion, TodoWrite
---

When this skill is invoked:

## Phase 0 — Preconditions (hard gate)

1. Read `.claude/ndvkit/ndvkit.config.json` (`specsRoot`, `matrixRoot`, `verifyNote`, `rulesRoot`,
   `kitRulesRoot`). Resolve rule files hai tầng theo `/ndv-audit-code` Step 0 — host tier (toàn bộ
   `<rulesRoot>/**` + `CLAUDE.md`) trước, kit tier (file per lens) sau — đúng bộ file audit sẽ
   chấm; chỉ truyền PATH cho agent. Orchestrator đọc body host tier (cho step 4), không đọc body
   kit tier. Spec folder `<specsRoot>/<NNN>_<MODULE>/` = field `spec` của entry
   modules.json, chưa có → Glob `<specsRoot>/*_<MODULE>/` (`NNN` = thứ tự implement, README §Quy
   ước chung).
2. `<specsRoot>/<NNN>_<MODULE>/plan.md` AND `tasks.md` both have `approved: true` —
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
4. **Host rule gate** — host rule mô tả trạng thái project phải đúng NGAY BÂY GIỜ, không phải mục
   tiêu về sau. Mỗi rule hay decision đã chốt trong host tier khẳng định trạng thái repo (folder /
   path tồn tại hay đã dời, giá trị config, owner của scene / prefab, file hay pattern bị cấm) →
   check bằng Glob / Grep / Read; đoạn chỉ mô tả code hiện có thì không thuộc gate. Repo lệch → STOP, không spawn. Ghi chú trong plan.md / tasks.md / deviation thừa nhận lệch
   (vd "X chưa thực hiện") KHÔNG phải approval. AskUserQuestion:
   (a) đưa repo về đúng rule trước — orchestrator liệt kê bước (vd dời folder, cite-only edit theo
   `/ndv-sync`); user approve → orchestrator làm như một bước riêng trước Phase 1, verify theo
   `verifyNote`, ghi vào report;
   (b) user đổi host rule cho khớp thực tế, ghi `decision: <yyyy-mm-dd>` vào rule — skill không
   tự sửa host rule;
   (c) dừng run.
5. Xác định cơ chế verify build/compile của project (`verifyNote` config;
   nếu rỗng, hỏi user một lần và đề nghị điền vào config). Nếu cơ chế cần
   service/tool đang không chạy (vd editor bridge, build server), request
   user chuẩn bị trước khi tiếp tục.
6. `--continue` resumes from the first unchecked task; `--phase <n>` runs one
   phase only; default runs phases sequentially with a gate between each.

## Phase 1 — Execute per phase

MỘT instance `module-implementer` (model: sonnet) cho cả run: spawn ở phase đầu, các lần
sau RESUME đúng instance đó (rules + plan + specify đã nằm trong context của nó). Spawn
instance mới chỉ khi harness không resume được, hoặc agent báo context gần đầy — khi đó prompt
mới ghi rõ phase nào đã xong.

For each phase in tasks.md:

1. Snapshot `git status --porcelain` (baseline). Spawn / resume `module-implementer` (Task
   tool, model: sonnet) với: module id, phase cần chạy, paths tới plan.md + specify.md +
   tasks.md, rule files (Phase 0 step 1), write scope (module `paths` + `<specsRoot>/<NNN>_<MODULE>/tasks.md` + files tasks name
   under no module's `paths` + stopgap-approved files). Hành vi (no scope expansion, test
   policy, no commit) là contract của agent — không restate trong prompt.
2. On agent return:
   - **blocked with question** → AskUserQuestion, then resume the same instance with the answer.
   - **blocked: prerequisite <owner> <what>** → the same three options as Phase 0 step 3.
   - **blocked: host-rule <file#section>** → host rule thắng plan.md / tasks.md. AskUserQuestion:
     plan sai → dừng, gửi về `/ndv-plan`; repo lệch rule → các option của Phase 0 step 4. Không
     resume implementer để làm theo plan trái host rule.
   - **spec-drift finding** → present Finding/Evidence/Impact to the user;
     route: minor → fix spec inline (sync specify.md/plan.md, A→B replace);
     major → stop, send back to `/ndv-specify`/`/ndv-plan`.
   - **completed** → verify: tasks checked in tasks.md, files exist, then
     build/compile check theo cơ chế verify của project (lỗi mới = phase
     chưa done — resume the same instance with the errors). Còn lỗi sau vòng compile-fix
     thứ 2 của phase → spawn MỘT instance `module-implementer` mới (Task tool, model: opus)
     với phase đó + error delta + files đã đổi, thử một lần; vẫn lỗi → STOP, báo user kèm
     error + files changed. Phase kế tiếp resume lại instance sonnet, prompt nêu files
     instance opus đã sửa.

     Scope check: `git status --porcelain` minus the baseline — every changed/new path must be
     inside the write scope (platform sidecar files, vd `.meta`, follow their asset). A path
     under another module's `paths` = phase NOT done: feed it back to the agent to revert, or
     AskUserQuestion for a stopgap (Phase 0 step 3c). Host without git → run the same check on
     the agent's returned file list.

     **Phase review** (sau compile sạch + scope check; phase không đổi file code nào → bỏ qua):
     spawn (Task tool) `subagent_type: code-auditor`, model: sonnet, vai FINDER, lens `patterns`
     + `spec`, scope = file code đổi trong phase (`git status --porcelain` minus baseline, bỏ
     tasks.md và sidecar `.meta`), spec = specify.md + plan.md, rule files Phase 0 step 1. Agent
     type chưa đăng ký → fallback như `/ndv-audit-code` Step 1. Candidate ≥ `medium` → resume
     implementer với candidate records: fix theo Fix hoặc refute kèm evidence (cite plan / spec)
     → compile lại theo vòng compile-fix ở trên. `low` / `info` → chỉ liệt kê ở gate. MỘT vòng
     review mỗi phase; orchestrator không phân xử candidate bị refute — ghi vào report phase.
3. Gate between phases: report files changed + deviations + phase review (raised / fixed /
   refuted / low-info listed); continue unless the user intervened or a gate in tasks.md says
   stop for review.

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
     `/ndv-module-matrix <MODULE>` (Skill tool — skill đó spawn `module-architect` Mode
     module, model: sonnet): promote planned edge thành `deps` kèm `depEvidence`. Không có gì
     để promote → KHÔNG spawn `module-architect`. Stack script không hỗ trợ / không có Python
     → luôn invoke skill đó.
   - `… ndv_check.py --refresh-status <MODULE> --write` — `status` re-derive theo
     `/ndv-module-matrix` §Status lifecycle + sinh lại `modules.md` (skill trên đã chạy thì
     bước này đã nằm trong nó).
   Bỏ qua bước này để lại `register-lag` `medium` cho `/ndv-audit-code` tìm thấy.
2. Cite sweep: run
   `python3 .claude/ndvkit/skills/ndv-sync/scripts/ndv_check.py --checks code-cite --touched <files changed this run>`
   (no Python on the host → Grep `<specsRoot>` for the changed file names and verify each
   cite per `/ndv-sync` Phase 1). Report every `broken-cite` with its owning artifact and
   the route from `/ndv-sync` Phase 2. Fixing them is a cite-only edit (`/ndv-sync` §Cite-only
   edit) — never bundled silently into this run.
3. Report: host rule gate result, phases done, files written, deviations, verify result, phase
   review tally, cite sweep result.
4. Next step: `/ndv-audit-code module <MODULE>`. Không commit trừ khi user yêu cầu.
