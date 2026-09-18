---
name: ndv-implement
description: "Bước 4d pipeline ndvkit (SDD implement): thực thi tasks.md đã approve cho một module, phase-by-phase qua agent module-implementer, verify build/compile theo cơ chế của project host, dừng ở gate giữa các phase. Dùng sau khi plan + tasks đều approved."
argument-hint: "<module-id> [--phase <n>] [--continue]"
user-invocable: true
allowed-tools: Read, Glob, Grep, Write, Edit, Bash, Task, AskUserQuestion, TodoWrite
---

When this skill is invoked:

## Phase 0 — Preconditions (hard gate)

1. Read `.claude/ndvkit/ndvkit.config.json` (`specsRoot`, `matrixRoot`,
   `verifyNote`). Rule source: host `.claude/rules/**` + `CLAUDE.md` nếu có; domain
   nào host không define → dùng kit default rules tại `.claude/ndvkit/rules/**`.
   Host thắng khi mâu thuẫn.
2. `<specsRoot>/<MODULE>/plan.md` AND `tasks.md` both have `approved: true` —
   else STOP and point at the missing gate. Never implement from an
   unapproved artifact.
3. Xác định cơ chế verify build/compile của project (`verifyNote` config;
   nếu rỗng, hỏi user một lần và đề nghị điền vào config). Nếu cơ chế cần
   service/tool đang không chạy (vd editor bridge, build server), request
   user chuẩn bị trước khi tiếp tục.
4. `--continue` resumes from the first unchecked task; `--phase <n>` runs one
   phase only; default runs phases sequentially with a gate between each.

## Phase 1 — Execute per phase

For each phase in tasks.md:

1. Spawn `module-implementer` (Task tool) with: module id, the phase's tasks,
   paths to plan.md + specify.md, and the standing reminder: tuân
   `.claude/rules/**` + `CLAUDE.md` host, no scope expansion, test policy
   theo host, no commit.
2. On agent return:
   - **blocked with question** → AskUserQuestion, then respawn with the
     answer.
   - **spec-drift finding** → present Finding/Evidence/Impact to the user;
     route: minor → fix spec inline (sync specify.md/plan.md, A→B replace);
     major → stop, send back to `/ndv-specify`/`/ndv-plan`.
   - **completed** → verify: tasks checked in tasks.md, files exist, then
     build/compile check theo cơ chế verify của project (lỗi mới = phase
     chưa done — feed back to the agent to fix).
3. Gate between phases: report files changed + deviations; continue unless
   the user intervened or a gate in tasks.md says stop for review.

## Phase 2 — Registration/manual steps

If the host module convention requires registration artifacts (config asset,
DI wiring, manifest entry…), perform them theo đúng cơ chế host quy định
(generator/menu/tool — không hand-author artifact mà host rules cấm
hand-author).

## Phase 3 — Close

1. All tasks `[x]` → close the register in one `/ndv-module-matrix <MODULE>` run
   (NOT `--render-only`): every `plannedDeps` edge the new code now references
   is promoted to `deps` with a grep-matched `depEvidence` cite
   (`<path>::<Type>.<Member>`), a planned edge the code still does not
   reference stays planned, and `status` is re-derived per `/ndv-module-matrix`
   §Status lifecycle (code present, no `FAIL` audit → `implemented`);
   the run re-renders index.html. Skipping this leaves a `register-lag` `medium`
   for `/ndv-audit-module` to find.
2. Report: phases done, files written, deviations, verify result.
3. Next step: `/ndv-audit-module <MODULE>`. Không commit trừ khi user yêu cầu.
