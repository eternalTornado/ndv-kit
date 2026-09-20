---
name: ndv-sync
description: "Bước 6 pipeline ndvkit: delta orchestrator — khi GDD/TDD/ModuleMatrix/requirement/specify/plan/code đổi, detect artifact nào downstream bị stale và route đúng skill update (mọi skill trong kit đều idempotent). Dùng khi 'GDD vừa update', 'có module mới', 'spec đổi rồi', hoặc muốn health-check toàn pipeline."
argument-hint: "[gdd|tdd|matrix|spec|code <target>] [--check-only] [--reanchor]"
user-invocable: true
allowed-tools: Read, Glob, Grep, Bash, Write, Edit, Task, Skill, AskUserQuestion, TodoWrite
---

When this skill is invoked:

## Phase 0 — Config & rules

Read `.claude/ndvkit/ndvkit.config.json` for all roots. Host
`.claude/rules/**` + `CLAUDE.md` là rule source ưu tiên; domain nào host không define
→ dùng kit default rules tại `.claude/ndvkit/rules/**`. Host thắng khi mâu thuẫn.

## Parse arguments

- `gdd|tdd|matrix|spec|code <target>` — the artifact tier that changed and
  its path/id. Omitted → full pipeline health-check (Phase 1 over
  everything).
- `--check-only` — report staleness, run nothing.
- `--reanchor` — bulk-convert legacy `<file>:<line>` code anchors that still land into
  symbol cites (see §Re-anchor). Runs instead of Phases 1–3.

## Phase 1 — Staleness detection

The pipeline chain is `GDD → TDD → ModuleMatrix → requirement.md →
specify.md → plan.md → tasks.md → code`. An artifact is STALE when its
upstream source changed after it was last written. Detect with evidence:

1. `git log -1 --format=%cI --invert-grep --grep='ndv-cite-only: true' -- <path>` per artifact
   (fallback: filesystem mtime for untracked files) — cite-only commits skip the timestamp
   (§Cite-only edit).
2. For a declared change (`gdd <path>` etc.), start at that tier and walk
   downstream only.
3. Content-level check where timestamps lie: TDD cites GDD anchors — Grep the
   anchors still exist; requirement cites TDD sections — same; modules.json
   `deps[]` vs actual import/using graph; plan.md `approved` flag predates a
   specify.md rewrite → approval is void.
   Artifact cites code: for every `<file>::<Symbol>` (and legacy `<file>.<ext>:<N>`) found in
   `<tddRoot>/**`, `<specsRoot>/**`, `<matrixRoot>/modules.json` — file exists under
   `codeRoots` AND the symbol grep-matches in it (legacy line anchor: the line still holds
   the quoted text or the symbol named beside it); a miss is `broken-cite`; a legacy
   line-only anchor that still lands is `legacy-line-anchor` (informational — convert with
   `--reanchor`); a cite that resolves only by unique basename/suffix is `inexact-path`
   (informational).
   Artifact cites doc/rule: every cite into `<rulesRoot>`, `<kitRulesRoot>`, `<tddRoot>`,
   `<specsRoot>`, `<gddRoot>` found in `<tddRoot>/**`, `<specsRoot>/**`, `CLAUDE.md` and
   `<rulesRoot>/**` — the file exists on disk and a `#section` names an existing heading;
   a miss is `broken-cite`.
   Contract: every Contract surface / Consumer obligations row of every requirement.md and
   specify.md carries an `Owner FR` / `Consumer FR` id that Grep-matches in that module's
   requirement.md; otherwise `contract-gap` (a `stopgap — …` row is reported, not a gap).
   `unowned-code` (informational): under a module's `paths`, code files changed after that
   module's requirement.md last content commit that introduce a public type or serialized field
   no FR of that requirement.md names.
4. The cite, contract and deps checks are deterministic — run them with the kit checker
   from the repo root instead of re-deriving them by hand:
   `python3 .claude/ndvkit/skills/ndv-sync/scripts/ndv_check.py [--checks doc-cite,code-cite,contract-gap,deps] [--json]`
   (Windows: `python` / `py -3`; stdlib only). `deps` is opt-in and covers the languages
   the script declares; other stacks → Grep the import/using graph. No Python on the
   host → perform the same checks with Grep. `unowned-code` is not in the script.
   `… ndv_check.py --refresh-status` (không `--write` = dry-run) liệt kê entry modules.json có
   `status` lệch `/ndv-module-matrix` §Status lifecycle → `status-drift`.

## Cite-only edit

A change whose diff touches ONLY cite tokens (path, `#section`, `::Symbol`, `:line`) — no
requirement text, value, decision or task.

1. It does not void `approved: true` on plan.md/tasks.md and does not make downstream artifacts
   stale.
2. It comes from `ndv_check.py --reanchor --write` (cite-only by construction) or from a
   manual fix — a manual fix shows its diff to the user in the report.
3. When the user commits, cite-only edits go in their own commit whose message carries
   the trailer `ndv-cite-only: true`; Phase 1 timestamps skip those commits:
   `git log -1 --format=%cI --invert-grep --grep='ndv-cite-only: true' -- <path>`.
   A commit that mixes cite fixes with content changes is a content change.

## Phase 2 — Impact report

Present a table: artifact → status (`fresh | stale | broken-cite | void-approval |
contract-gap | status-drift | legacy-line-anchor | inexact-path | unowned-code`) → evidence →
skill to run.
Example routes:

| Change | Route |
|---|---|
| GDD section edited | `/ndv-gdd-to-tdd <feature> --update` → then re-walk |
| TDD mới / TDD deps đổi | `/ndv-module-matrix <feature>` + `/ndv-tdd-to-spec <feature>` |
| Module mới xuất hiện trong code | `/ndv-module-matrix` (registration + layer) |
| requirement.md đổi | `/ndv-specify <MODULE>` |
| specify.md đổi sau khi plan approved | `/ndv-plan <MODULE>` (re-approve) |
| plan.md đổi sau khi tasks approved | `/ndv-tasks <MODULE>` (re-approve) |
| code đổi ngoài pipeline (hotfix) | `/ndv-audit-code module <MODULE>` (drift check) |
| Audit kết luận code đúng, spec sai (Triage `spec-fix`) | `/ndv-specify <MODULE> --from-audit <report>` — owner của việc viết lại FR theo as-built; TDD/GDD nói khác code → `/ndv-gdd-to-tdd <Feature> --update` sau khi Design sửa GDD |
| `status-drift` | `ndv_check.py --refresh-status --write` (không cần skill, không spawn agent) |
| Code anchor `broken-cite`, symbol still exists elsewhere (moved/renamed file, shifted line) | cite-only edit at the owning artifact: TDD → `tdd-writer` (Mode brownfield, cite-only); requirement.md → `spec-writer` (cite-only); specify/plan/tasks → edit the cite in place. Approved plan/tasks keep their approval (§Cite-only edit) |
| Code anchor `broken-cite`, symbol gone (behaviour removed or replaced) | not cite-only — content drift: `/ndv-audit-code module <MODULE>`, then the owning skill of the artifact |
| Doc/rule `broken-cite` | cite-only edit: point the cite at the file that exists on disk (rule files: `<kitRulesRoot>/…` unless the host adopted a copy under `<rulesRoot>`) |
| `legacy-line-anchor` / `inexact-path` | `/ndv-sync --reanchor` |
| `contract-gap` | `/ndv-specify <consumer MODULE>` Phase 4 (contract back-propagation) |
| `unowned-code` | `/ndv-onboard reverse-doc <MODULE>`, or `/ndv-specify <consumer>` Phase 4 when a consumer's contract row is the source |

`--check-only` stops here.

## Phase 3 — Guided execution

1. AskUserQuestion: which stale chains to update now (multiSelect).
2. Invoke the selected skills (Skill tool) in upstream→downstream order, one tier at a time —
   each tier's output feeds the next tier's input, no skipping. Ngoài skill này và
   `/ndv-implement` Phase 3 (→ `/ndv-module-matrix`), không skill nào trong kit tự invoke skill
   khác — chỗ khác chỉ nêu lệnh để user chạy.
3. Approval gates are NOT bypassed: a re-run `/ndv-plan`/`/ndv-tasks` asks for
   approval again — sync never self-approves.
4. Report: chains updated, artifacts written, gates awaiting user.

## Re-anchor (`--reanchor`)

1. Dry run: `python3 .claude/ndvkit/skills/ndv-sync/scripts/ndv_check.py --reanchor` —
   present the `old → new` table grouped by artifact, plus the anchors it leaves alone
   (`broken-cite`, `quoted-anchor`, `reanchor-unsupported`).
2. AskUserQuestion: apply all / apply per artifact / cancel. Apply = the same command with
   `--write`, restricted with `--artifact <file> ...` when the user picked a subset.
3. Report files changed, remind the commit rule of §Cite-only edit, list what is still
   `broken-cite` — those need a human decision, the script never guesses a moved symbol.
   No Python on the host → do the conversion per artifact by opening each cited file (R3).
