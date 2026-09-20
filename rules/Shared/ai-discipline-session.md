# AI Discipline — session rules (R6, R8–R10)

> Phần của bộ R1–R10 dành cho main session / orchestrator (đối thoại với user, đề xuất, quản
> trị SoT). Worker core R1–R5 + R7: [ai-discipline.md](ai-discipline.md) — đọc file đó trước.
> Số R giữ nguyên để cite `§R-NN` cũ vẫn đúng nghĩa.

---

## R6 — Follow chosen workflow, direct answer

User chốt workflow → tuân thủ, không tự đề xuất skip / alternative.

Hỏi → pick MỘT phương án + execute + cite, không "Option A vs B vs C" trừ khi:

- User yêu cầu compare
- Quyết định irreversible / breaking → dùng AskUserQuestion với 2-3 option

AI scope:

- AI chỉ implement task + file area được giao
- Không tự nghĩ gameplay rule
- Không đổi balance constant
- Không refactor ngoài scope
- Không mở rộng change nếu không có source + human approval

---

## R8 — Proposals: grounded, holistic, concise

Mọi đề xuất (artifact hoặc chat) MUST:

1. **Grounded**: research (web / codebase / GDD) trước, KHÔNG gut-feel
2. **Cite**: mỗi point ≥1 source
3. **Holistic**: tổng thể + trade-off, không mảnh rời
4. **Concise**: proposal + cite + scope; cấm bullet "for completeness"
5. **Anti ad-hoc**: chưa research kịp → nói "cần research thêm về X trước khi propose"

**Format**:

```text
Đề xuất: <action>
Source: <path#section hoặc path::Symbol / URL + quote ≤2 câu>
Trade-off: <≤1 câu impact / cost>
```

---

## R9 — Single Source of Truth: cite-back, never duplicate

Mỗi fact / value / taxonomy / threshold / decision / rule có **đúng 1 canonical location**.
Cite-back (`[name](path)` hoặc `<path>#<section>`), KHÔNG restate body.

**Canonical location index** — mỗi project MAINTAIN một bảng map content → SoT trong host
rules. Khi host chưa có, default của kit:

| Content | Canonical SoT |
|---|---|
| AI behavior rules R1–R5, R7 | [ai-discipline.md](ai-discipline.md) |
| AI behavior rules R6, R8–R10 | file này |
| Core principles, governance, writing | `Shared/constitution.md` |
| Id allocation invariants | `Shared/id-plan.md` (giá trị cụ thể: host rules) |
| Naming per stack | stack rules (`Unity/conventions.md`, `Server/server.md`…) |
| Trust boundary (authority) | `Unity/security.md` |
| Module dependency hiện trạng | `<matrixRoot>/modules.json` (register, pipeline sinh) |
| Module contract per module | `<specsRoot>/<MODULE>/` artifacts |
| GDD content (gameplay rules, balance) | `<gddRoot>/**` (Design managed) |
| Severity taxonomy (audit) | `ai-discipline.md` §R7 |
| Audit protocol (finder/verifier, evidence, severity guide) | agent `code-auditor` |
| Glossary (canonical term per domain) | host rules |
| Amendment history của rules kit | `CHANGELOG.md` |

**Allowed exceptions** (limited duplication):

- Literal quote ≤2 câu (R4 pattern)
- Header summary kèm pointer + ≤8 line digest
- Cross-file index (file name + 1-line description)
- Frontmatter redundancy cần cho artifact tự chứa

**BANNED**: restate entire taxonomy / threshold / enum ở >1 file; re-define same convention
với wording khác; paraphrase canonical rule body.

### R9.1 — Body vs history separation

**Body** của artifact = current state. **History / lifecycle** sống ở single sources:
frontmatter `created`/`updated`, STATUS/changelog doc per system (nếu project có), git log;
rules của kit: [CHANGELOG.md](../CHANGELOG.md).

**BANNED inline body decoration**: `chốt <date>`, `RESOLVED <date>`, `patched <date>`,
`(Recommended)`, "Đã chốt", "Đã apply" trong body text.

**Allowed**: gate confirm checkbox với date (event record), frontmatter date field,
changelog entry theo format R7, factual evidence cite (gồm cite `decision:` theo R3).

---

## R10 — Enterprise register

Mọi AI output (assistant message + doc body + commit msg + PR description + skill output)
dùng formal register. Không slang / casual.

**BANNED slang / casual**: `bắn agent`/`phang code` (→ `invoke`/`implement`), `ngon`/`chạy
luôn không` (→ `acceptable`/`proceed?`), `Just/Simply/Obviously` (xóa hoặc cite lý do),
`Yeah/Nope` (→ `Yes/No`), `gut-feel`/`hên xui` (→ `untested`/`unverified`).

Ambiguous quantifier: banned list tại [ai-discipline.md](ai-discipline.md) §R5.

Ngôn ngữ tự nhiên của team OK (technical term giữ English); chỉ ban slang/casual register.

---

## Exception — Justified Deviation

Nếu MUST vi phạm R1–R10, artifact phải có section `## Complexity Justification` gồm:

1. Rule nào vi phạm
2. Lý do (cite source bắt buộc)
3. Scope + thời lượng
4. Plan return về compliance

Không có section này = vi phạm.

---

## Enforcement

- `/ndv-audit-code` của kit và audit skill riêng của host (nếu có) flag vi phạm theo format
  R7 + severity.
- Human review: code review flag vi phạm; AI không self-approve.

## Governance

Amendment cho R1–R10 theo [constitution.md](constitution.md): written rationale + migration
note, ghi tại [CHANGELOG.md](../CHANGELOG.md).
