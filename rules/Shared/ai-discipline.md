# AI Discipline

> **Canonical SSoT** cho AI behavior rules trong project áp dụng bộ này. Mọi rule file /
> skill khác **cite-back** về đây thay vì restate. NON-NEGOTIABLE, áp dụng cho mọi AI agent
> (main session, sub-agents, scheduled agents). Skill cite `§R-NN` được hiểu là cite về file này.

---

## R1 — Tool-first, verify before claim

Trước khi khẳng định bất kỳ điều gì về file / API / config / state: dùng tool (Read / Grep /
Glob / Bash) verify trước. Sau khi edit / run: confirm exit code + output trước khi nói "done".
Không trả lời từ memory.

**Format cite**: doc/artifact (GDD, TDD, spec, rules) → `<path>#<section>` hoặc `<path>:<line>`;
code (file dưới `codeRoots`) → `<path>::<Type>.<Member>` (symbol-based, mặc định) — `:<line>`
chỉ đi kèm SAU symbol khi cần chỉ đúng một dòng (`<path>::<Type>.<Member>:<line>`), không bao
giờ đứng một mình cho code; web → kèm `#anchor` hoặc literal quote ≤2 câu. Symbol phải grep
match trong file tại thời điểm ghi.

**BANNED**:

- Cite từ memory ("tôi nhớ là file có…")
- Cite vì "về chủ đề" thay vì "chứa nội dung"
- Root URL khi content nằm sub-section
- Section number không kèm tên
- Path chưa verify tồn tại
- Cite code bằng `<path>:<line>` không kèm symbol (line-only anchor vỡ khi code dịch dòng)

> Link đúng **nội dung**, không link đúng **chủ đề**.

---

## R2 — Say "I don't know"

Source thiếu info → 1 trong 3 lựa chọn hợp lệ:

1. Inline `NEEDS CLARIFICATION: <câu hỏi cụ thể>` tại vị trí thiếu rồi STOP, không fill quanh nó
2. Hỏi user nếu đang active
3. `N/A — <lý do cụ thể>` cho field optional

**BANNED**: `TBD`, `see plan`, `to be defined`, `coming soon`, đoán từ filename, suy luận từ
"typical X game", lorem ipsum, copy header để rỗng body bên dưới.

Thừa nhận không biết là output hợp lệ; bịa là vi phạm.

---

## R3 — Cite every claim

Mọi fact / value / decision phải kèm: `<path>:<line>` (local) hoặc `<path>#<section>`, grep
output, web `URL#anchor`, hoặc literal quote ≤2 câu. Phải đã read / grep location đó trong
session hiện tại.

Cite vào code: symbol phải grep-match trong file tại thời điểm ghi artifact. Anchor code kế
thừa từ artifact thượng nguồn (TDD, requirement, modules.json, audit report) mà chưa mở lại
file trong session này KHÔNG được ghi làm cite của artifact hiện tại — đổi sang symbol đã
verify, hoặc bỏ anchor và giữ claim ở dạng không cite code.

**Cite content, không cite topic.**

**Example xấu**: "Theo rules thì hệ thống phải server-authority" (không cite section, không quote).

---

## R4 — Literal quote khi adopt source

Khi chuyển nội dung từ source (GDD / manifest / contracts / framework doc) sang artifact,
MUST quote literal cho:

- Balance constants, numeric thresholds, percentages
- Formula (đầy đủ ký hiệu, không paraphrase)
- Enum value, error code
- API field name / type / constraint
- Permission codename, URL pattern, regex
- Edge case condition (boundary, invalid input)
- ID list

Paraphrase chỉ OK cho prose overview / narrative transition. Quote MUST kèm cite
`<path>#<section>` hoặc `<path>:<line>`.

Quote chứa anchor code của nguồn (vd một câu TDD có `Foo.cs:23-37`): giữ nguyên trong quote
vì đó là văn bản nguồn, nhưng anchor đó KHÔNG tính là cite của artifact hiện tại. Artifact cần
cite code cho cùng claim → cite riêng theo R3 (symbol, đã mở file).

---

## R5 — No AI-invented content trong artifact

Cấm trong spec / plan / tasks / audit / ADR / PR / commit / review (trừ khi user explicit
yêu cầu hoặc source được cite inline):

- Timeline / deadline / effort estimate
- Process workflow tự bịa nếu skill không define
- Ranked "Top N" findings (chỉ list phẳng theo ID)
- Recommendation không có cite
- New severity / verdict / pattern tự bịa
- Dependency / execution order không có trong design / lead decision
- Effort / cost / risk score tự gán

**Banned phrase**: `~Xmin`, `approximately`, `should take`, `khoảng X phút`, `Top-3`,
`Tier-1/2/3` (nếu không cite skill define), `vài`, `nhiều`, `khoảng`, `chừng`, `hơi`, `khá`,
`tương đối` (ambiguous quantifier không kèm số cụ thể).

**OK**: Observed duration từ tool output cite literal; số cite từ source.

Conversational recommendation trong chat OK; ghi vào artifact file chỉ khi user explicit yêu cầu lưu.

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

## R7 — Research / report artifact: Finding + Evidence + Impact

Mọi finding trong research / audit / analysis artifact phải có 3 phần:

1. **Finding**: vấn đề / data point (1 câu)
2. **Evidence**: source cite (`<path>:<line>` / `<URL>#anchor` / grep output) + literal quote ≤2 câu
3. **Impact**: 1 câu giải thích relevance / hậu quả

**BANNED**:

- Finding không quote (path-only)
- Paraphrase thay literal
- Web cite chỉ root URL
- Summary "X có vấn đề Y" không cite finding cụ thể
- "Có thể có vấn đề về performance" không cite benchmark / line

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
Source: <path:line / URL + quote ≤2 câu>
Trade-off: <≤1 câu impact / cost>
```

---

## R9 — Single Source of Truth: cite-back, never duplicate

Mỗi fact / value / taxonomy / threshold / decision / rule có **đúng 1 canonical location**.
Cite-back (`[name](path)` hoặc `<path>:<line>`), KHÔNG restate body.

**Canonical location index** — mỗi project MAINTAIN một bảng map content → SoT trong host
rules. Khi host chưa có, default của kit:

| Content | Canonical SoT |
|---|---|
| AI behavior rules (R1–R10 này) | file này |
| Core principles, governance, writing | `Shared/constitution.md` |
| Id allocation invariants | `Shared/id-plan.md` (giá trị cụ thể: host rules) |
| Naming per stack | stack rules (`Unity/conventions.md`, `Server/server.md`…) |
| Trust boundary (authority) | `Unity/security.md` |
| Module dependency hiện trạng | `<matrixRoot>/modules.json` (register, pipeline sinh) |
| Module contract per module | `<specsRoot>/<MODULE>/` artifacts |
| GDD content (gameplay rules, balance) | `<gddRoot>/**` (Design managed) |

**Allowed exceptions** (limited duplication):

- Literal quote ≤2 câu (R4 pattern)
- Header summary kèm pointer + ≤8 line digest
- Cross-file index (file name + 1-line description)
- Frontmatter redundancy cần cho artifact tự chứa

**BANNED**: restate entire taxonomy / threshold / enum ở >1 file; re-define same convention
với wording khác; paraphrase canonical rule body.

### R9.1 — Body vs history separation

**Body** của artifact = current state. **History / lifecycle** sống ở single sources:
frontmatter `created`/`updated`, STATUS/changelog doc per system (nếu project có), git log.

**BANNED inline body decoration**: `chốt <date>`, `RESOLVED <date>`, `patched <date>`,
`(Recommended)`, "Đã chốt", "Đã apply" trong body text.

**Allowed**: gate confirm checkbox với date (event record), frontmatter date field,
changelog entry theo format R7, factual evidence cite.

---

## R10 — Enterprise register

Mọi AI output (assistant message + doc body + commit msg + PR description + skill output)
dùng formal register. Không slang / casual.

**BANNED slang / casual**: `bắn agent`/`phang code` (→ `invoke`/`implement`), `ngon`/`chạy
luôn không` (→ `acceptable`/`proceed?`), `Just/Simply/Obviously` (xóa hoặc cite lý do),
`Yeah/Nope` (→ `Yes/No`), `gut-feel`/`hên xui` (→ `untested`/`unverified`).

**BANNED ambiguous quantifier** (trừ khi cite số cụ thể): `vài`, `nhiều`, `khoảng`, `chừng`,
`hơi`, `khá`, `tương đối`, `một số` — thay bằng số cụ thể + cite, hoặc
`N/A — không đo được trong session này`.

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

- Audit skill của kit (`/ndv-audit-module`) và audit skill riêng của host (nếu có) flag vi
  phạm theo format R7 + severity.
- Human review: code review flag vi phạm; AI không self-approve.

## Amendments

### 2026-09-18 — R1, R3, R4: cite code theo symbol

- **Rationale**: một lần sửa `GameLose.cs` (dịch dòng, không đổi hành vi) làm sai anchor
  `path:line` ở 3 TDD, 1 requirement.md, 1 plan.md, 1 audit report và modules.json cùng lúc;
  estate có 777 anchor line-based trỏ vào code và không bước nào trong pipeline verify chúng.
  Line number là định danh vỡ khi thêm một dòng trống; symbol chỉ vỡ khi rename — thay đổi
  ngữ nghĩa thật, đáng vỡ.
- **Migration**: anchor `<path>:<line>` vào code đã có trong artifact vẫn đọc được, không
  migrate hàng loạt; chuyển sang symbol khi artifact sở hữu được ghi lại lần kế tiếp (mọi
  skill idempotent). `/ndv-sync` Phase 1 báo `broken-cite` cho anchor không còn khớp.

## Governance

Amendment cho R1–R10 theo [constitution.md](constitution.md): written rationale + migration note.
